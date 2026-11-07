import json

from fastapi.testclient import TestClient

from shop.app import create_app
from shop.staff import save_staff


def test_admin_can_edit_shipping_tiers():
    client = TestClient(create_app(units_per_usd=1, db_path=":memory:"))
    conn = client.app.state.db
    save_staff(conn, "admin", "secret-pass", "admin")
    login = client.post("/admin/login", data={"username": "admin", "password": "secret-pass"}, follow_redirects=False)
    assert login.status_code == 303
    client.cookies.update(login.cookies)

    page = client.get("/admin/promos")
    assert page.status_code == 200
    assert 'name="ship_USCA"' in page.text
    assert 'name="ship_MXBR"' in page.text

    saved = client.post(
        "/admin/promos",
        data={
            "free_shipping_cents": "3900",
            "first_over": "1500",
            "first_off": "500",
            "tier_over": ["3000", "6000"],
            "tier_off": ["400", "800"],
            "ship_USCA": "500",
            "ship_EU": "800",
            "ship_JP": "700",
            "ship_MXBR": "900",
        },
        follow_redirects=False,
    )
    assert saved.status_code == 303
    raw = conn.execute("select value from promos where key='shipping'").fetchone()["value"]
    shipping = json.loads(raw)
    assert shipping == {"USCA": 500, "EU": 800, "JP": 700, "MXBR": 900}

    cart = client.get("/cart?country=US")
    assert cart.status_code == 200
    # empty cart may not show fee; add item then check
    client.post("/cart/add", data={"sku": "oil-sprayer", "qty": "1", "country": "US"}, follow_redirects=False)
    cart = client.get("/cart?country=US")
    assert 'data-shipping-cents="500"' in cart.text or "$5.00" in cart.text
