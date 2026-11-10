from datetime import timedelta

from shop.db import connect
from shop.lucky import (
    iso,
    load_settings,
    lookup_off,
    on_paid,
    on_refund,
    save_settings,
    smash,
    spin,
    utcnow,
)
from shop.pricing import quote


def memory():
    conn = connect(":memory:")
    conn.execute(
        """
        create table settings (key text primary key, value text not null)
        """
    )
    conn.execute(
        """
        create table orders (
            id integer primary key,
            email text,
            status text,
            merchandise_cents integer,
            discount_cents integer,
            coupon_cents integer,
            referrer_email text,
            created_at text
        )
        """
    )
    conn.execute("create table balances (email text primary key, available_cents integer not null)")
    return conn


def add_order(conn, email, status, goods, referrer=""):
    result = conn.execute(
        """
        insert into orders (
            email, status, merchandise_cents, discount_cents, coupon_cents, referrer_email, created_at
        ) values (?, ?, ?, 0, 0, ?, ?)
        """,
        (email, status, goods, referrer, iso(utcnow())),
    )
    return result.lastrowid


def test_spin_is_always_the_configured_percent_and_uncapped():
    conn = memory()
    token = spin(conn, "")
    assert lookup_off(conn, token, "", 100000) == 10000
    assert spin(conn, token) == token
    bill = quote(
        merchandise_cents=100000,
        tiers=[],
        coupon_cents=500,
        coupon_threshold_cents=0,
        free_shipping_cents=0,
        shipping_cents=0,
        balance_cents=0,
        use_balance=False,
        units_per_usd=1,
        minor_units=2,
        lucky_off_cents=10000,
    )
    assert bill.discount_cents == 10000
    assert bill.coupon_cents == 500
    assert bill.due_cents == 89500


def test_one_free_order_and_it_must_be_the_latest_paid_order():
    conn = memory()
    first = add_order(conn, "a@shop.test", "paid", 2000)
    second = add_order(conn, "a@shop.test", "paid", 2500)
    refused = smash(conn, "a@shop.test", first)
    assert refused["ok"] is False
    assert refused["code"] == "not_latest"
    won = smash(conn, "a@shop.test", second)
    assert won["ok"] is True
    assert won["free"]["order_id"] == second
    assert won["free"]["amount_cents"] == 2500
    again = smash(conn, "a@shop.test", second)
    assert again["code"] == "already"
    other = add_order(conn, "a@shop.test", "paid", 3000)
    assert smash(conn, "a@shop.test", other)["code"] == "already"


def test_later_orders_and_one_friend_fill_stamps_then_credit_after_the_window():
    conn = memory()
    save_settings(conn, {"enabled": "1", "stamps_needed": "2", "return_days": "0", "window_days": "60"})
    bound = add_order(conn, "a@shop.test", "paid", 2000)
    assert smash(conn, "a@shop.test", bound)["ok"] is True
    own = add_order(conn, "a@shop.test", "paid", 2000)
    on_paid(conn, own)
    moved = conn.execute("select order_id, stamps, amount_cents from lucky_frees where email = ?", ("a@shop.test",)).fetchone()
    assert moved["order_id"] == own
    assert moved["stamps"] == 1
    assert moved["amount_cents"] == 2000
    friend = add_order(conn, "b@shop.test", "paid", 2000, referrer="a@shop.test")
    on_paid(conn, friend)
    again = add_order(conn, "b@shop.test", "paid", 5000, referrer="a@shop.test")
    on_paid(conn, again)
    row = conn.execute("select stamps, status from lucky_frees where email = ?", ("a@shop.test",)).fetchone()
    assert row["stamps"] == 2
    assert row["status"] == "paid"
    balance = conn.execute("select available_cents from balances where email = ?", ("a@shop.test",)).fetchone()
    assert balance["available_cents"] == 2000
    small = add_order(conn, "c@shop.test", "paid", 1000, referrer="a@shop.test")
    on_paid(conn, small)
    assert conn.execute("select count(*) as n from lucky_stamps").fetchone()["n"] == 2


def test_refund_of_the_bound_order_voids_and_a_stamp_refund_removes_that_stamp():
    conn = memory()
    save_settings(conn, {"enabled": "1", "stamps_needed": "5", "return_days": "30"})
    bound = add_order(conn, "a@shop.test", "paid", 2000)
    smash(conn, "a@shop.test", bound)
    extra = add_order(conn, "a@shop.test", "paid", 2000)
    on_paid(conn, extra)
    moved = conn.execute("select order_id, stamps from lucky_frees where email = ?", ("a@shop.test",)).fetchone()
    assert moved["order_id"] == extra
    assert moved["stamps"] == 1
    conn.execute("update orders set status = 'refunded' where id = ?", (bound,))
    on_refund(conn, bound)
    open_row = conn.execute("select stamps, status, order_id from lucky_frees where email = ?", ("a@shop.test",)).fetchone()
    assert open_row["stamps"] == 0
    assert open_row["status"] == "open"
    assert open_row["order_id"] == extra
    conn.execute("update orders set status = 'refunded' where id = ?", (extra,))
    on_refund(conn, extra)
    voided = conn.execute("select status from lucky_frees where email = ?", ("a@shop.test",)).fetchone()
    assert voided["status"] == "void"


def test_pages_and_admin_settings_are_wired():
    from fastapi.testclient import TestClient

    from shop.app import create_app
    from shop.staff import save_staff

    client = TestClient(create_app(units_per_usd=150, db_path=":memory:"))
    home = client.get("/")
    assert home.status_code == 200
    assert 'id="lucky"' in home.text
    assert "data-lucky-spin" in home.text
    assert "/static/lucky.min.css?v=2" in home.text
    guest = client.get("/api/lucky").json()
    assert guest["offer_spin"] is True
    assert guest["first_order"] is True
    assert guest["spin"] is None
    spun = client.post("/api/lucky/spin")
    assert spun.status_code == 200
    assert spun.json()["spin"]["percent"] == 10
    assert spun.json()["spin"]["live"] is True
    assert spun.json()["first_order"] is True
    after = client.get("/api/lucky").json()
    assert after["offer_spin"] is False
    assert after["first_order"] is True
    bought = client.get("/api/lucky", cookies={"harbor_bought": "1"}).json()
    assert bought["first_order"] is False
    js = client.get("/static/lucky.min.js").text
    assert "function showOffChip()" in js
    assert "state.first_order&&state.spin&&state.spin.live" in js
    assert "else if(state.offer_spin)chip.hidden=false" not in js
    save_staff(client.app.state.db, "admin", "secret-pass", "admin")
    entered = client.post(
        "/admin/login",
        data={"username": "admin", "password": "secret-pass"},
        follow_redirects=False,
    )
    assert entered.status_code == 303
    page = client.get("/admin/lucky")
    assert page.status_code == 200
    assert "一人一条" in page.text
    saved = client.post(
        "/admin/lucky",
        data={"enabled": "1", "percent": "10", "hours": "6", "browse_minutes": "3", "stamps_needed": "5", "window_days": "60", "return_days": "30"},
        follow_redirects=False,
    )
    assert saved.status_code == 303
    assert client.get("/admin/lucky").status_code == 200


def test_expired_spin_is_not_replaced():
    conn = memory()
    token = spin(conn, "", "", now=utcnow() - timedelta(hours=7))
    assert lookup_off(conn, token, "", 5000, now=utcnow()) == 0
    assert spin(conn, token) == token
    assert load_settings(conn)["percent"] == 10
