from fastapi.testclient import TestClient

from shop.app import create_app
from shop.staff import save_staff
from shop.storefront_theme import get_storefront_theme, set_storefront_theme


def _admin(client):
    save_staff(client.app.state.db, "admin", "secret-pass", "admin")
    login = client.post(
        "/admin/login",
        data={"username": "admin", "password": "secret-pass"},
        follow_redirects=False,
    )
    assert login.status_code == 303
    client.cookies.update(login.cookies)


def test_storefront_defaults_to_legacy_html():
    client = TestClient(create_app(units_per_usd=1, db_path=":memory:"))
    assert get_storefront_theme(client.app.state.db) == "legacy"
    home = client.get("/")
    assert home.status_code == 200
    assert "theme-pimo" not in home.text
    assert "pimo-home" not in home.text
    assert "product-grid" in home.text
    assert "/static/pimo.css" not in home.text


def test_admin_appearance_persists_pimo_and_legacy():
    client = TestClient(create_app(units_per_usd=1, db_path=":memory:"))
    _admin(client)
    page = client.get("/admin/appearance")
    assert page.status_code == 200
    assert 'name="storefront_theme"' in page.text
    assert "满减运费" in page.text

    saved = client.post(
        "/admin/appearance",
        data={"storefront_theme": "pimo"},
        follow_redirects=False,
    )
    assert saved.status_code == 303
    assert get_storefront_theme(client.app.state.db) == "pimo"

    home = client.get("/")
    assert home.status_code == 200
    assert "theme-pimo" in home.text
    assert 'class="pimo-home"' in home.text
    assert 'class="pimo-search"' in home.text
    assert "/search?country=US" in home.text
    assert 'action="/cart/add"' in home.text
    assert 'name="ajax" value="1"' in home.text
    assert "pimo-tab" in home.text
    assert "Free shipping — no tiers, no wait." in home.text
    assert "express" not in home.text.lower()
    assert "/static/dept/kitchen.svg" not in home.text

    ignored = set_storefront_theme(client.app.state.db, "nope")
    assert ignored == "pimo"

    back = client.post(
        "/admin/appearance",
        data={"storefront_theme": "legacy"},
        follow_redirects=False,
    )
    assert back.status_code == 303
    assert get_storefront_theme(client.app.state.db) == "legacy"
    legacy = client.get("/")
    assert "theme-pimo" not in legacy.text
    assert "product-grid" in legacy.text


def test_pimo_add_uses_cart_api():
    client = TestClient(create_app(units_per_usd=1, db_path=":memory:"))
    set_storefront_theme(client.app.state.db, "pimo")
    added = client.post(
        "/cart/add",
        data={"sku": "drain-rack", "qty": "1", "country": "US", "ajax": "1"},
        headers={"X-Harbor-Ajax": "1", "Accept": "application/json"},
    )
    assert added.status_code == 200
    body = added.json()
    assert body["ok"] is True
    assert body["cart_count"] >= 1
    assert body.get("ship_met") is True
    home = client.get("/")
    assert 'data-pimo-count' in home.text
