from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from shop.app import create_app
from shop.fx import NoRate, Rate

BUYER = {
    "email": "buyer@example.com",
    "name": "A Buyer",
    "address": "1 Road",
    "city": "Osaka",
    "region": "Osaka",
    "postal": "5300001",
    "phone": "09000000000",
}


class BrokenBook:
    def rate_for(self, currency, now):
        if currency == "USD":
            return Rate(1.0, False)
        raise NoRate(currency)


@pytest.fixture()
def client():
    app = create_app(units_per_usd=150, db_path=":memory:")
    return TestClient(app)


def _address(**extra):
    data = dict(BUYER)
    data.update(extra)
    return data


def test_buy_now_keeps_the_existing_cart(client):
    added = client.post(
        "/cart/add",
        data={"sku": "binder-clip", "qty": "1", "country": "JP"},
        follow_redirects=False,
    )
    assert added.status_code == 303
    assert "binder-clip:1" in added.cookies["cart"]
    bought = client.post(
        "/buy",
        data={"sku": "drain-rack", "qty": "1", "country": "JP"},
        follow_redirects=False,
    )
    assert bought.cookies["checkout_line"] == "drain-rack:1"
    assert client.cookies["cart"] == "binder-clip:1"
    cart = client.get("/cart?country=JP")
    assert "バインダークリップ" in cart.text
    assert 'data-shipping-cents="0"' in cart.text
    checkout = client.get("/checkout?country=JP&buy=1")
    assert "水切りラック" in checkout.text
    assert "バインダークリップ" not in checkout.text


def test_cart_page_recommends_products(client):
    empty = client.get("/cart?country=US")
    assert "For you" in empty.text
    assert 'class="card"' in empty.text
    client.post("/cart/add", data={"sku": "binder-clip", "qty": "1", "country": "US"})
    filled = client.get("/cart?country=US")
    assert "Add a little more" in filled.text
    assert 'class="card" href="/p/binder-clip?country=US"' not in filled.text


def test_product_shipping_uses_visit_country_and_order_uses_ship_to(client):
    japan = client.get("/p/drain-rack?country=JP")
    assert "送料無料" in japan.text
    united = client.get("/p/drain-rack?country=US")
    assert "Free shipping on orders over" in united.text
    client.post("/cart/add", data={"sku": "drain-rack", "qty": "1", "country": "JP"})
    response = client.post(
        "/checkout?country=JP",
        data=_address(ship_country="US", submit_id="ship-us", coupon_id=""),
    )
    assert response.status_code == 200
    order = client.app.state.db.execute("select * from orders").fetchone()
    assert order["shipping_cents"] == 0
    assert order["currency"] == "JPY"
    assert order["due_cents"] == 1200
    assert order["due_local"] == 1800
    assert "data-due-local=\"1800\"" in response.text


def test_same_submit_id_creates_one_order(client):
    client.post("/cart/add", data={"sku": "drain-rack", "qty": "1", "country": "JP"})
    payload = _address(ship_country="JP", submit_id="same-id", coupon_id="")
    first = client.post("/checkout?country=JP", data=payload)
    second = client.post("/checkout?country=JP", data=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    rows = client.app.state.db.execute("select id from orders").fetchall()
    assert len(rows) == 1
    stock = client.app.state.db.execute(
        "select stock from products where sku = 'drain-rack'"
    ).fetchone()["stock"]
    assert stock == 99
    assert len(client.app.state.outbox.messages) == 1
    mail = client.app.state.outbox.messages[0]
    assert mail["to"] == "buyer@example.com"
    assert "JPY" in mail["body"]
    assert str(rows[0]["id"]) in mail["body"]


def test_balance_row_is_locked_across_two_checkouts():
    from shop.checkout import place_order

    app = create_app(units_per_usd=150, db_path=":memory:")
    db = app.state.db
    db.execute(
        "insert into balances (email, available_cents) values ('buyer@example.com', 500)"
    )
    promos = db.execute("select key, value from promos").fetchall()
    import json
    loaded = {row["key"]: json.loads(row["value"]) for row in promos}
    loaded["tiers"] = [tuple(pair) for pair in loaded["tiers"]]

    def submit(index):
        place_order(
            db,
            loaded,
            app.state.outbox,
            lines=[{"sku": "binder-clip", "qty": 1}],
            submit_id=f"bal-{index}",
            email="buyer@example.com",
            name="A Buyer",
            address="1 Road",
            city="Austin",
            region="TX",
            postal="73301",
            ship_country="US",
            phone="5551212",
            currency="USD",
            units=1,
            minor_units=2,
            use_balance=True,
            coupon_id=None,
            referrer=None,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(submit, (0, 1)))
    spent = db.execute("select coalesce(sum(balance_cents), 0) as n from orders").fetchone()["n"]
    left = db.execute(
        "select available_cents from balances where email = 'buyer@example.com'"
    ).fetchone()["available_cents"]
    assert spent == 500
    assert left == 0


def test_short_stock_is_marked_and_cancel_restores_it(client):
    db = client.app.state.db
    db.execute("update products set stock = 1 where sku = 'drain-rack'")
    client.post("/cart/add", data={"sku": "drain-rack", "qty": "2", "country": "JP"})
    short = client.post(
        "/checkout?country=JP",
        data=_address(ship_country="JP", submit_id="short", coupon_id=""),
    )
    assert 'data-stock="drain-rack"' in short.text
    assert db.execute("select count(*) as n from orders").fetchone()["n"] == 0
    assert db.execute("select stock from products where sku = 'drain-rack'").fetchone()["stock"] == 1
    db.execute("update products set stock = 5 where sku = 'drain-rack'")
    placed = client.post(
        "/checkout?country=JP",
        data=_address(ship_country="JP", submit_id="placed", coupon_id=""),
    )
    assert placed.status_code == 200
    order_id = db.execute("select id from orders").fetchone()["id"]
    assert db.execute("select stock from products where sku = 'drain-rack'").fetchone()["stock"] == 3
    cancelled = client.post(f"/orders/{order_id}/cancel")
    assert cancelled.status_code == 200
    assert db.execute("select status from orders where id = ?", (order_id,)).fetchone()["status"] == "cancelled"
    assert db.execute("select stock from products where sku = 'drain-rack'").fetchone()["stock"] == 5


def test_zero_stock_cannot_be_added(client):
    client.app.state.db.execute("update products set stock = 0 where sku = 'toy-ball'")
    response = client.post(
        "/cart/add",
        data={"sku": "toy-ball", "qty": "1", "country": "US"},
        follow_redirects=False,
    )
    assert "cart" not in response.cookies
    assert "cart" not in client.cookies


def test_guest_sets_password_then_login_sees_the_order(client):
    client.post("/cart/add", data={"sku": "note-holder", "qty": "1", "country": "US"})
    placed = client.post(
        "/checkout?country=US",
        data=_address(ship_country="US", submit_id="guest", coupon_id=""),
    )
    assert "order" in placed.text.lower() or "Order" in placed.text or "注文" in placed.text or "Bestell" in placed.text
    order = client.app.state.db.execute("select * from orders").fetchone()
    order_id = order["id"]
    assert f"{order_id}" in placed.text
    client.post(f"/orders/{order_id}/pay")
    client.post(
        "/stripe/webhook",
        json={
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"order_id": str(order_id)},
                    "currency": order["currency"].lower(),
                    "amount_total": order["due_local"],
                }
            },
        },
    )
    saved = client.post(f"/orders/{order_id}/password", data={"password": "correct horse"})
    assert saved.status_code == 200
    client.post("/login", data={"email": "buyer@example.com", "password": "correct horse"})
    orders = client.get("/account/orders?country=US")
    assert str(order_id) in orders.text


def test_reset_link_expires_after_thirty_minutes(client):
    client.post("/cart/add", data={"sku": "note-holder", "qty": "1", "country": "US"})
    client.post(
        "/checkout?country=US",
        data=_address(ship_country="US", submit_id="reset", coupon_id=""),
    )
    client.post(f"/orders/1/password", data={"password": "old-password"})
    client.post("/reset-password", data={"email": "buyer@example.com"})
    mail = client.app.state.outbox.messages[-1]
    token = mail["body"].split("token=")[1]
    db = client.app.state.db
    db.execute(
        "update password_resets set expires_at = ? where token = ?",
        ("2000-01-01T00:00:00+00:00", token),
    )
    rejected = client.post("/reset-password", data={"token": token, "password": "new-password"})
    assert rejected.status_code == 400
    login = client.post(
        "/login",
        data={"email": "buyer@example.com", "password": "new-password"},
        follow_redirects=False,
    )
    assert login.status_code == 401
    fresh = client.post("/reset-password", data={"email": "buyer@example.com"})
    assert fresh.status_code == 200
    new_token = client.app.state.outbox.messages[-1]["body"].split("token=")[1]
    accepted = client.post(
        "/reset-password",
        data={"token": new_token, "password": "new-password"},
        follow_redirects=False,
    )
    assert accepted.status_code == 303
    client.post("/login", data={"email": "buyer@example.com", "password": "new-password"})
    assert "buyer_session" in client.cookies


def test_japan_example_stores_4200_yen(client):
    db = client.app.state.db
    db.execute(
        "insert into balances (email, available_cents) values ('buyer@example.com', 500)"
    )
    coupon = db.execute("select id from coupons where kind = 'public'").fetchone()["id"]
    client.post("/cart/add", data={"sku": "oil-sprayer", "qty": "5", "country": "JP"})
    response = client.post(
        "/checkout?country=JP",
        data=_address(ship_country="JP", submit_id="yen-4200", coupon_id=str(coupon), use_balance="1"),
    )
    order = db.execute("select * from orders").fetchone()
    assert order["discount_cents"] == 300
    assert order["coupon_cents"] == 300
    assert order["shipping_cents"] == 0
    assert order["balance_cents"] == 500
    assert order["due_cents"] == 2900
    assert order["due_local"] == 4350
    assert order["self_rebate_cents"] == 170
    assert order["direct_rebate_cents"] == 0
    assert order["status"] == "pending"
    left = db.execute("select available_cents from balances").fetchone()["available_cents"]
    assert left == 0
    assert 'data-due-local="4350"' in response.text


def test_missing_field_and_missing_rate_do_not_create_an_order(client):
    client.post("/cart/add", data={"sku": "note-holder", "qty": "1", "country": "US"})
    missing = client.post(
        "/checkout?country=US",
        data=_address(phone="", ship_country="US", submit_id="miss", coupon_id=""),
    )
    assert 'data-field="phone"' in missing.text
    assert client.app.state.db.execute("select count(*) as n from orders").fetchone()["n"] == 0
    broken = TestClient(create_app(book=BrokenBook(), db_path=":memory:"))
    broken.post("/cart/add", data={"sku": "note-holder", "qty": "1", "country": "JP"})
    page = broken.get("/p/note-holder?country=JP")
    assert page.status_code == 200
    refused = broken.post(
        "/checkout?country=JP",
        data=_address(ship_country="JP", submit_id="no-rate", coupon_id=""),
    )
    assert refused.status_code == 200
    assert broken.app.state.db.execute("select count(*) as n from orders").fetchone()["n"] == 0


def test_checkout_page_still_quotes_an_empty_cart(client):
    page = client.get("/checkout?country=JP")
    assert 'data-due-local="0"' in page.text
    assert "data-ad" not in page.text
