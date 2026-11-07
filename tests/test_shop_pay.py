import hashlib
import hmac
import os
import time

import pytest
from fastapi.testclient import TestClient

from shop.app import create_app
from shop.checkout import hash_password, verify_password

BUYER = {
    "email": "buyer@example.com",
    "name": "A Buyer",
    "address": "1 Road",
    "city": "Austin",
    "region": "TX",
    "postal": "73301",
    "phone": "5551212",
}


@pytest.fixture()
def client():
    return TestClient(create_app(units_per_usd=150, db_path=":memory:"))


def available(db, email):
    row = db.execute(
        "select available_cents from balances where email = ?",
        (email,),
    ).fetchone()
    return 0 if row is None else row["available_cents"]


def grants(db, email, kind):
    return db.execute(
        """
        select count(*) as n from coupon_grants g
        join coupons c on c.id = g.coupon_id
        where g.email = ? and c.kind = ?
        """,
        (email, kind),
    ).fetchone()["n"]


def place(client, sku="note-holder", country="US", ship="US", submit_id="order-1"):
    client.post("/cart/add", data={"sku": sku, "qty": "1", "country": country})
    payload = dict(BUYER)
    payload.update(ship_country=ship, submit_id=submit_id, coupon_id="")
    client.post(f"/checkout?country={country}", data=payload)
    return client.app.state.db.execute("select * from orders order by id desc").fetchone()


def pay(client, order, currency=None, amount=None):
    page = client.post(f"/orders/{order['id']}/pay")
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"order_id": str(order["id"])},
                "currency": currency or order["currency"].lower(),
                "amount_total": order["due_local"] if amount is None else amount,
            }
        },
    }
    result = client.post("/stripe/webhook", json=event)
    return page, result


def login(client, email="buyer@example.com"):
    client.app.state.db.execute(
        """
        insert into accounts (email, password_hash, referrer_email)
        values (?, ?, null)
        on conflict(email) do update set password_hash = excluded.password_hash
        """,
        (email, hash_password("correct horse")),
    )
    client.post("/login", data={"email": email, "password": "correct horse"})


def test_stripe_uses_order_currency_and_pays_rebates_once(client):
    order = place(client, sku="drain-rack", country="JP", ship="JP", submit_id="yen")
    assert available(client.app.state.db, "buyer@example.com") == 0
    page, _ = pay(client, order)
    assert f'data-currency="jpy"' in page.text
    assert f'data-amount="{order["due_local"]}"' in page.text
    session = client.app.state.stripe.checkouts[-1]
    assert session["currency"] == "jpy"
    assert session["amount"] == order["due_local"]
    paid = client.app.state.db.execute("select status, self_rebate_cents from orders where id = ?", (order["id"],)).fetchone()
    assert paid["status"] == "paid"
    assert available(client.app.state.db, "buyer@example.com") == paid["self_rebate_cents"]
    pay(client, order)
    assert available(client.app.state.db, "buyer@example.com") == paid["self_rebate_cents"]


def test_wrong_currency_event_leaves_the_order_unpaid(client):
    order = place(client, sku="drain-rack", country="JP", ship="JP", submit_id="bad-event")
    client.post(f"/orders/{order['id']}/pay")
    client.post(
        "/stripe/webhook",
        json={
            "type": "checkout.session.completed",
            "data": {"object": {"metadata": {"order_id": str(order["id"])}, "currency": "usd", "amount_total": order["due_local"]}},
        },
    )
    status = client.app.state.db.execute("select status from orders where id = ?", (order["id"],)).fetchone()["status"]
    assert status == "pending"
    assert available(client.app.state.db, "buyer@example.com") == 0


def test_own_link_pays_one_rebate_and_upper_balance_stays(client):
    db = client.app.state.db
    db.execute(
        "insert into accounts (email, password_hash, referrer_email) values ('upper@example.com', null, null)"
    )
    db.execute("insert into balances (email, available_cents) values ('upper@example.com', 80)")
    db.execute("insert into referrals (email, code) values ('buyer@example.com', 'own')")
    opened = client.get("/r/own", follow_redirects=False)
    assert "max-age=31536000" in opened.headers["set-cookie"].lower()
    order = place(client, submit_id="own-link")
    assert order["direct_rebate_cents"] == 0
    assert order["self_rebate_cents"] > 0
    assert available(db, "buyer@example.com") == 0
    pay(client, order)
    assert available(db, "buyer@example.com") == order["self_rebate_cents"]
    assert available(db, "upper@example.com") == 80


def test_referral_cookie_sticks_and_later_orders_keep_paying_them(client):
    db = client.app.state.db
    db.execute("insert into accounts (email, password_hash, referrer_email) values ('a@example.com', null, null)")
    db.execute(
        "insert into accounts (email, password_hash, referrer_email) values ('b@example.com', null, 'a@example.com')"
    )
    db.execute("insert into referrals (email, code) values ('b@example.com', 'bcode')")
    db.execute("insert into referrals (email, code) values ('a@example.com', 'acode')")
    first = client.get("/r/bcode", follow_redirects=False)
    assert "max-age=31536000" in first.headers["set-cookie"].lower()
    client.get("/r/acode", follow_redirects=False)
    assert client.cookies.get("referrer_code") == "bcode"
    first_order = place(client, submit_id="ref-1")
    assert first_order["referrer_email"] == "b@example.com"
    assert first_order["direct_rebate_cents"] > 0
    assert available(db, "b@example.com") == 0
    assert available(db, "a@example.com") == 0
    pay(client, first_order)
    assert available(db, "b@example.com") == first_order["direct_rebate_cents"]
    assert available(db, "a@example.com") == 0
    client.cookies.delete("referrer_code")
    second = place(client, sku="toy-ball", submit_id="ref-2")
    assert second["referrer_email"] == "b@example.com"
    pay(client, second)
    assert available(db, "b@example.com") == first_order["direct_rebate_cents"] + second["direct_rebate_cents"]
    assert available(db, "a@example.com") == 0


def test_refund_claws_back_available_rebate_and_restores_stock(client):
    db = client.app.state.db
    order = place(client, submit_id="refund-me")
    pay(client, order)
    db.execute(
        "update balances set available_cents = 5 where email = 'buyer@example.com'"
    )
    from shop.staff import save_staff

    save_staff(db, "admin", "secret", "admin")
    try:
        denied = client.post(f"/admin/orders/{order['id']}/refund", follow_redirects=False)
        assert denied.status_code == 401
        client.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)
        client.post(f"/admin/orders/{order['id']}/refund", follow_redirects=False)
    finally:
        os.environ.pop("ADMIN_PASSWORD", None)
    status = db.execute("select status from orders where id = ?", (order["id"],)).fetchone()["status"]
    stock = db.execute("select stock from products where sku = 'note-holder'").fetchone()["stock"]
    assert status == "refunded"
    assert stock == 100
    assert available(db, "buyer@example.com") == 0
    assert client.app.state.stripe.refunds[-1]["currency"] == "usd"
    assert client.app.state.stripe.refunds[-1]["amount"] == order["due_local"]


def test_share_desktop_and_checkin_grants_are_limited(client):
    db = client.app.state.db
    client.post("/share", data={"email": ""})
    assert grants(db, "friend@example.com", "share") == 0
    client.post("/share", data={"email": "friend@example.com"})
    client.post("/share", data={"email": "friend@example.com"})
    assert grants(db, "friend@example.com", "share") == 1
    client.post("/desktop", data={"email": "friend@example.com"})
    client.post("/desktop", data={"email": "friend@example.com"})
    assert grants(db, "friend@example.com", "desktop") == 1
    lonely = client.post("/check-in")
    assert lonely.status_code == 401
    login(client, "friend@example.com")
    client.post("/check-in")
    client.post("/check-in")
    assert grants(db, "friend@example.com", "checkin") == 1


def test_withdrawal_minimum_is_ten_dollars(client):
    db = client.app.state.db
    login(client)
    db.execute(
        "insert into balances (email, available_cents) values ('buyer@example.com', 2500)"
    )
    rejected = client.post("/account/withdraw", data={"amount_cents": "999", "payout": "bank-1"})
    assert rejected.status_code == 400
    assert db.execute("select count(*) as n from withdrawals").fetchone()["n"] == 0
    accepted = client.post("/account/withdraw", data={"amount_cents": "1000", "payout": "bank-1"})
    assert accepted.status_code == 200
    assert db.execute("select amount_cents, status from withdrawals").fetchone()["amount_cents"] == 1000
    assert available(db, "buyer@example.com") == 1500


def test_shipped_buyer_can_review_each_product_once(client):
    db = client.app.state.db
    order = place(client, submit_id="ship-me")
    pay(client, order)
    from shop.staff import save_staff

    save_staff(db, "admin", "secret", "admin")
    try:
        too_soon = client.post(
            f"/admin/orders/{order['id']}/ship",
            data={"carrier": "ParcelPost", "tracking": "TRK900"},
            follow_redirects=False,
        )
        assert too_soon.status_code == 401
        client.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)
        early = client.post(
            "/p/note-holder/review",
            data={"rating": "5", "body": "Useful"},
            follow_redirects=False,
        )
        assert early.status_code == 401
        client.post(f"/orders/{order['id']}/password", data={"password": "correct horse"})
        client.post("/login", data={"email": "buyer@example.com", "password": "correct horse"})
        client.post("/p/note-holder/review", data={"rating": "5", "body": "Useful"}, follow_redirects=False)
        assert db.execute("select count(*) as n from reviews").fetchone()["n"] == 0
        client.post(
            f"/admin/orders/{order['id']}/ship",
            data={"carrier": "ParcelPost", "tracking": "TRK900"},
            follow_redirects=False,
        )
    finally:
        os.environ.pop("ADMIN_PASSWORD", None)
    page = client.get(f"/orders/{order['id']}?country=US")
    assert "ParcelPost" in page.text
    assert "TRK900" in page.text
    client.post("/p/note-holder/review", data={"rating": "5", "body": "Useful"}, follow_redirects=False)
    client.post("/p/note-holder/review", data={"rating": "4", "body": "Again"}, follow_redirects=False)
    rows = db.execute("select rating, body from reviews").fetchall()
    assert len(rows) == 1
    assert rows[0]["body"] == "Useful"


def test_checkout_has_no_delivery_speed_choice(client):
    client.post("/cart/add", data={"sku": "note-holder", "qty": "1", "country": "US"})
    page = client.get("/checkout?country=US")
    assert page.status_code == 200
    assert 'name="speed"' not in page.text
    assert "Express" not in page.text


def test_account_password_is_saved(client):
    login(client)
    short = client.post("/account/password", data={"password": "short"}, follow_redirects=False)
    assert short.status_code == 400
    saved = client.post("/account/password", data={"password": "new-secret"}, follow_redirects=False)
    assert saved.status_code == 303
    stored = client.app.state.db.execute(
        "select password_hash from accounts where email = 'buyer@example.com'"
    ).fetchone()["password_hash"]
    assert verify_password("new-secret", stored)
    guest = TestClient(create_app(units_per_usd=150, db_path=":memory:"))
    denied = guest.post("/account/password", data={"password": "long-enough"}, follow_redirects=False)
    assert denied.status_code == 303
    assert "/login" in denied.headers["location"]


def test_offer_sale_reduces_the_parent_stock(client):
    db = client.app.state.db
    db.execute(
        "update products set stock = 4, offers = ? where sku = 'note-holder'",
        ('[{"id":"red","label":"Red","price_cents":1000}]',),
    )
    client.post("/cart/add", data={"sku": "note-holder", "offer": "red", "qty": "2", "country": "US"})
    payload = dict(BUYER)
    payload.update(ship_country="US", submit_id="sku-stock", coupon_id="")
    client.post("/checkout?country=US", data=payload)
    stock = db.execute("select stock from products where sku = 'note-holder'").fetchone()["stock"]
    assert stock == 2
    icon = client.get("/apple-touch-icon.png")
    assert icon.status_code == 200
    assert icon.headers["content-type"].startswith("image/png")


def test_lianlian_sign_string_matches_the_published_example():
    from shop.pay import _rsa_sign, _private_key, sign_factor

    payload = {
        "c": {"b": "11", "a": "10"},
        "a": "100",
        "b": [{"f": "3", "e": "2", "d": "1"}, {"j": "6", "i": "5", "h": "4"}],
    }
    assert sign_factor(payload) == "a=100&d=1&e=2&f=3&h=4&i=5&j=6&a=10&b=11"
    factors = {
        "merchant_id": "202103310000636001",
        "merchant_transaction_id": "202111121816050188",
    }
    private = (
        "MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCoa1NW2hNLDtdFTSq4WJveRtwbzkSjUoJmhQPrpf3PvUacHnAGnB6aYF0Kww2bsRgZKht2Otl2aYn7wG1Za562uyVzRtZ/6EFRJ47cjQtjKX7dSJj5918o7ou6GENm0PZchJIQuCs4r26i0Z+0ClTAx4jBZcd9aJv3uI/49na3ltDLOqRO8IRB9MDfECbRAKjgbkfRTKxR98FKhjzMkNQP2ji8LjHkOULv6TEG9PbR6/f8xIG3w3CnEAa+ZvATStBR7FyaMUTsQlK66LGeyAeDwWhRsL9TXSI0R7eCbwjU3Hd6qD8MuOuclvwiN4L7g8Ls3XO3Z/oEucEl6auF7dwTAgMBAAECggEBAKfCQEFC9/TL06I0O1lk6d1+t8D6tWP5y+pSlJUlwqwq3SqlJvFukQ0073jI0cVDob1vM+uQswxAFDGwezuW94EM6UDqTr8ZmfY8cRE/bRhZPQUuSzKyNReQhZ3YjUrc2olNhDEjQeo01P9ZzrqHj+R23MHHn+5LRRB7xu02kwpKjPz0u73VO3Bzvh3+ZAbJaEzu7+XeFkmzIVscPHQHmhGJUPbcIaS7r2jKx1QkSfRNyM1yTLLCLuQxG6HOTDNeshdT2m2AE0gtuWhYZ1W+aTgLs7jUgCM8sAJbxw0hSz05wUNpGxkJmMe7+KzsVu8ZSa9FbDtT9kZZq4t7Ch01wAECgYEA8qvMfkxuvjSBIAwoWnM4fKJCzTPkWsn2ZCVVPEgd9jfnMAKvXX/0FfGdOAnQOqyoqZfHCiF8g56sCipbPB/naExn9DpSSeq1iYbWGxBFwGktSkbTMzmCaSDH9pQ44640+s4UCLLEf5cakEim2PEH0sZD1gH+yhntJO+w2MPhraECgYEAsat4d6GP2tyTkjKK7Xm2q6c9T52ah5ZGNvC+9uqU8dLKfa5Gg5KWKdaqJwxIQZIYZmG/Hxi6fvPviEzalNKXtt5XSX+kP33IAtekWKJwdlNX9h5o3nR4g57/dzubMdTQp1oXWvxyOAAiUVYoPcLD/21ROdDEWXoL6Z56ftXgJTMCgYEAzvvAOX3B+5RXCtmz1apvZMcVyWdYgCPBeBvrvrYYcDmwhF/V6h9INytVmUWtiU5ZsgXWbIqxZKaDQUxtczQXMfvxsvvH0mpSm1IZ7w2LIRnU2oTcgdWsqTSfum8ksvaVE9OQfPbV6aodqzF8to+nx5z6oWAkTYedoSKcqdcx9+ECgYBIwpcwLurxz3lj2u0IOds0SuYR79I0CrewkkEyb3kV26RveeqIwYRbl/zQxvfkWodBjnAttPvTN+T1pbuyTNgy3LVUdUB3e/RoLZWxcrypyJHyShvaVkpwZLHsS23QJ35Xus5rxYylIHDtbGJIgLWxqjwkeDmhBxlP0EYMIVyM/wKBgFhFzzM89TosVINLOjwDMFNUIEc0ujgXkcjojIQv2cBYSXBsbyW3uySFiFVBh+p6acWq4K03yIVuIS2pnAkpkF1bqop0FdfAFiXDtEOtTHMaYj2pSihk6lc8ohJ5PRkZ+C30ObamBR3hlqhteBv8D6+6g5By9QonqUe4ktZ7QugA"
    )
    from shop.pay import _public_key, _rsa_verify

    signed = _rsa_sign(_private_key(private), sign_factor(factors))
    public = (
        "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAqGtTVtoTSw7XRU0quFib3kbcG85Eo1KCZoUD66X9z71GnB5wBpwemmBdCsMNm7EYGSobdjrZdmmJ+8BtWWuetrslc0bWf+hBUSeO3I0LYyl+3UiY+fdfKO6LuhhDZtD2XISSELgrOK9uotGftApUwMeIwWXHfWib97iP+PZ2t5bQyzqkTvCEQfTA3xAm0QCo4G5H0UysUffBSoY8zJDUD9o4vC4x5DlC7+kxBvT20ev3/MSBt8NwpxAGvmbwE0rQUexcmjFE7EJSuuixnsgHg8FoUbC/U10iNEe3gm8I1Nx3eqg/DLjrnJb8IjeC+4PC7N1zt2f6BLnBJemrhe3cEwIDAQAB"
    )
    assert _rsa_verify(_public_key(public), sign_factor(factors), signed)


def test_stripe_webhook_signature_rejects_a_bad_digest():
    from shop.db import connect, migrate
    from shop.pay import StripeCheckout

    conn = connect(":memory:")
    migrate(conn)
    gate = StripeCheckout(conn, "sk_test", "whsec_test")
    payload = b"{}"
    stamp = str(int(time.time()))
    digest = hmac.new(b"whsec_test", f"{stamp}.".encode() + payload, hashlib.sha256).hexdigest()
    assert gate.valid_signature(payload, f"t={stamp},v1={digest}")
    assert not gate.valid_signature(payload, f"t={stamp},v1=deadbeef")
