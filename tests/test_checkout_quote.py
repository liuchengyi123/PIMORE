from fastapi.testclient import TestClient

from shop.app import create_app
from shop.db import connect, migrate
from shop.tax import estimate_tax_cents

BUYER = {
    "email": "buyer@example.com",
    "name": "A Buyer",
    "address": "1 Road",
    "city": "Sacramento",
    "region": "CA",
    "postal": "95814",
    "phone": "5551212",
}


def _client():
    return TestClient(create_app(units_per_usd=150, db_path=":memory:"))


def _address(**extra):
    data = dict(BUYER)
    data.update(extra)
    return data


def test_estimate_is_half_up_and_splits_california_from_canada():
    # 400 cents * 7.25% = 29 exactly. 1000 cents * 7.25% = 72.5 → 73.
    assert estimate_tax_cents(400, "US", "CA") == 29
    assert estimate_tax_cents(400, "US", "California") == 29
    assert estimate_tax_cents(1000, "us", "ca") == 73
    assert estimate_tax_cents(400, "CA", "ON") == 20  # Canada GST, not California
    assert estimate_tax_cents(400, "US", "OR") == 0
    assert estimate_tax_cents(400, "JP", "Tokyo") == 0
    assert estimate_tax_cents(400, "US", "") == 0


def test_quote_us_ca_economy_matches_place_order_and_zero_tax():
    client = _client()
    added = client.post(
        "/cart/add",
        data={"sku": "note-holder", "qty": "1", "country": "US"},
        follow_redirects=False,
    )
    assert added.status_code == 303
    quoted = client.post(
        "/api/checkout/quote?country=US",
        json={
            "speed": "economy",
            "ship_country": "US",
            "region": "CA",
            "use_balance": False,
            "gift_message": "for mom",
            "gift_wrap": True,
        },
    )
    assert quoted.status_code == 200
    body = quoted.json()
    assert body["ok"] is True
    assert body["speed"] == "economy"
    assert body["shipping_cents"] == 0
    assert body["merchandise_cents"] == body["subtotal"] == 400
    assert body["discount_cents"] == 0
    assert body["coupon_cents"] == 0
    assert body["balance_cents"] == 0
    assert body["taxable_cents"] == 400
    assert body["tax_cents"] == 29
    assert body["tax_estimate"] is True
    assert body["tax_included_in_due"] is False
    assert body["due_cents"] == body["total"] == 400
    assert body["currency"] == "USD"
    assert body["lines"] == [
        {"sku": "note-holder", "qty": 1, "price_cents": 400, "line_cents": 400}
    ]
    assert body["blockers"] == []
    assert body["gift_message"] == "for mom"
    assert body["gift_wrap"] is True
    assert body["gift_sku"] == ""

    zero = client.post(
        "/api/checkout/quote?country=US",
        json={"speed": "economy", "ship_country": "US", "state": "OR"},
    )
    assert zero.status_code == 200
    z = zero.json()
    assert z["ok"] is True
    assert z["tax_cents"] == 0
    assert z["shipping_cents"] == 0
    assert z["due_cents"] == 400

    japan = client.post(
        "/api/checkout/quote?country=US",
        json={"speed": "economy", "ship_country": "JP", "region": "Tokyo"},
    )
    assert japan.json()["tax_cents"] == 0
    assert japan.json()["due_cents"] == 400

    placed = client.post(
        "/checkout?country=US",
        data=_address(ship_country="US", region="CA", submit_id="tax-ca", coupon_id="", gift="for mom"),
    )
    assert placed.status_code == 200
    order = client.app.state.db.execute("select * from orders").fetchone()
    assert order["tax_cents"] == body["tax_cents"] == 29
    assert order["due_cents"] == body["due_cents"] == 400
    assert order["shipping_cents"] == 0
    assert order["merchandise_cents"] == 400
    assert order["gift_message"] == "for mom"
    assert order["speed"] == "standard"


def test_express_quote_matches_charged_shipping_and_tax_base():
    client = _client()
    client.post("/cart/add", data={"sku": "note-holder", "qty": "1", "country": "US"})
    quoted = client.post(
        "/api/checkout/quote?country=US",
        json={"speed": "express", "ship_country": "US", "region": "CA"},
    )
    body = quoted.json()
    assert body["ok"] is True
    assert body["shipping_cents"] == 600
    assert body["taxable_cents"] == 1000
    assert body["tax_cents"] == 73
    assert body["due_cents"] == body["total"] == 1000
    placed = client.post(
        "/checkout?country=US",
        data=_address(
            ship_country="US",
            region="CA",
            submit_id="tax-express",
            coupon_id="",
            speed="express",
        ),
    )
    assert placed.status_code == 200
    order = client.app.state.db.execute("select * from orders").fetchone()
    assert order["shipping_cents"] == 600
    assert order["tax_cents"] == 73
    assert order["due_cents"] == 1000
    assert order["speed"] == "express"


def test_lucky_blocks_coupon_on_the_quote():
    client = _client()
    client.post("/cart/add", data={"sku": "oil-sprayer", "qty": "5", "country": "US"})
    spun = client.post("/api/lucky/spin")
    assert spun.status_code == 200
    blocked = client.post(
        "/api/checkout/quote?country=US",
        json={
            "speed": "economy",
            "ship_country": "US",
            "region": "CA",
            "coupon_code": "public",
        },
    )
    body = blocked.json()
    assert body["ok"] is True
    assert "coupon_blocked_by_lucky" in body["blockers"]
    assert body["coupon_cents"] == 0
    assert body["coupon_id"] is None
    # 4000 merchandise, tier 300, lucky 10% = 400 folded into discount.
    assert body["merchandise_cents"] == 4000
    assert body["discount_cents"] == 700
    assert body["taxable_cents"] == 3300
    assert body["due_cents"] == 3300
    # 3300 * 7.25% = 239.25 → 239
    assert body["tax_cents"] == 239


def test_migrate_adds_tax_cents_to_an_existing_orders_table(tmp_path):
    conn = connect(str(tmp_path / "old.sqlite"))
    conn.execute("create table orders (id integer primary key, email text not null default '')")
    migrate(conn)
    cols = {row["name"] for row in conn.execute("pragma table_info(orders)").fetchall()}
    assert "tax_cents" in cols
