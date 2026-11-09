"""Shopper controls that used to be dead: cart JSON, quote, tax admin, chat."""

from shop.staff import save_staff
from tests.test_checkout_quote import _address, _client


def test_cart_json_and_ajax_qty_keep_shipping_at_zero():
    client = _client()
    added = client.post(
        "/cart/add",
        data={"sku": "note-holder", "qty": "1", "country": "US", "ajax": "1"},
        headers={"Accept": "application/json"},
    )
    assert added.status_code == 200
    assert added.json()["ok"] is True
    snap = client.get("/api/cart")
    body = snap.json()
    assert body["ok"] is True
    assert body["shipping_cents"] == 0
    assert body["lines"][0]["sku"].startswith("note-holder")
    updated = client.post(
        "/cart/update",
        data={"sku": body["lines"][0]["sku"], "qty": "3", "ajax": "1", "country": "US"},
        headers={"Accept": "application/json"},
    )
    assert updated.status_code == 200
    assert updated.json()["shipping_cents"] == 0
    assert updated.json()["lines"][0]["qty"] == 3


def test_checkout_page_has_coupon_gift_and_tax_without_speed_choices():
    client = _client()
    client.post("/cart/add", data={"sku": "note-holder", "qty": "1", "country": "US"})
    page = client.get("/checkout?country=US")
    assert page.status_code == 200
    assert 'name="coupon_code"' in page.text
    assert 'name="gift_wrap"' in page.text
    assert 'name="gift"' in page.text
    assert "quote-tax" in page.text
    assert 'name="speed"' not in page.text
    assert "express" not in page.text.lower() or "data-shipping-cents" in page.text


def test_admin_tax_rate_changes_the_quote_and_gift_wrap_fee_is_editable():
    client = _client()
    conn = client.app.state.db
    save_staff(conn, "admin", "secret-pass", "admin")
    login = client.post(
        "/admin/login",
        data={"username": "admin", "password": "secret-pass"},
        follow_redirects=False,
    )
    assert login.status_code == 303
    client.cookies.update(login.cookies)
    page = client.get("/admin/tax")
    assert page.status_code == 200
    assert 'name="us_CA"' in page.text
    saved = client.post("/admin/tax", data={"us_CA": "10", "extra_country": "JP", "extra_percent": "8"}, follow_redirects=False)
    assert saved.status_code == 303
    wrap = client.post(
        "/admin/promos",
        data={"section": "gift", "gift_wrap_dollars": "1.00"},
        follow_redirects=False,
    )
    assert wrap.status_code == 303
    client.post("/cart/add", data={"sku": "note-holder", "qty": "1", "country": "US"})
    quoted = client.post(
        "/api/checkout/quote?country=US",
        json={"ship_country": "US", "region": "CA", "gift_wrap": True, "gift_message": "hi"},
    )
    body = quoted.json()
    assert body["shipping_cents"] == 0
    assert body["tax_cents"] == 40  # 10% of $4
    assert body["tax_included_in_due"] is False
    assert body["gift_wrap_fee_cents"] == 100
    assert body["gift_wrap_cents"] == 100
    assert body["due_cents"] == 500
    japan = client.post(
        "/api/checkout/quote?country=US",
        json={"ship_country": "JP", "region": "Tokyo", "gift_wrap": False},
    )
    assert japan.json()["tax_cents"] == 32  # 8% of $4
    assert japan.json()["gift_wrap_cents"] == 0


def test_buyer_chat_page_talks_to_cs_api():
    client = _client()
    page = client.get("/chat")
    assert page.status_code == 200
    assert "/api/cs/open" in page.text
    assert "/api/cs/send" in page.text
    opened = client.post("/api/cs/open", json={"sku": "note-holder", "name": "Notes"})
    assert opened.status_code == 200
    room = opened.json()["room"]["id"]
    sent = client.post("/api/cs/send", json={"room_id": room, "body": "where is my order"})
    assert sent.status_code == 200
    assert sent.json()["ok"] is True


def test_login_page_links_register_and_can_show_password():
    client = _client()
    page = client.get("/login")
    assert page.status_code == 200
    assert "/register" in page.text
    assert "/reset-password" in page.text
    assert "login-eye" in page.text
