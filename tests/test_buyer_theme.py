from pathlib import Path

from fastapi.testclient import TestClient

from shop.app import create_app
from shop.buyer_theme import (
    DEFAULT_ID,
    DERIVED_KEYS,
    TOKEN_KEYS,
    VERSION,
    derive,
    public_theme,
    save_active_id,
    ThemeError,
)
from shop.staff import save_staff

ROOT = Path(__file__).resolve().parents[1]


def test_public_theme_defaults_to_coral_market():
    client = TestClient(create_app(units_per_usd=1, db_path=":memory:"))
    res = client.get("/api/buyer-theme")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["version"] == VERSION == 1
    assert body["activeId"] == DEFAULT_ID
    tokens = body["pack"]["tokens"]
    assert list(tokens) == list(TOKEN_KEYS)
    assert tokens["color.primary"] == "#FF6A3D"
    assert tokens["color.primarySoft"] == "#FFD4C4"
    assert tokens["color.page"] == "#FFF4F0"
    assert tokens["color.ink"] == "#2C2623"
    assert tokens["color.surface"] == "#FFFFFF"
    assert tokens["color.onPrimary"] == "#FFFFFF"
    assert tokens["color.sale"] != tokens["color.primary"]
    assert tokens["color.badge"] != tokens["color.primary"]
    assert tokens["color.sale"] != tokens["color.badge"]
    assert body["pack"]["derived"] == derive(tokens)
    assert list(body["pack"]["derived"]) == list(DERIVED_KEYS)
    assert body["packs"] == [{"id": "coral-market", "name": "Coral Market"}]


def test_unknown_stored_id_falls_back_and_admin_can_select():
    client = TestClient(create_app(units_per_usd=1, db_path=":memory:"))
    conn = client.app.state.db
    conn.execute(
        "insert into settings (key, value) values ('buyer_theme', 'not-a-pack')"
    )
    assert public_theme(conn)["activeId"] == "coral-market"

    try:
        save_active_id(conn, "nope")
    except ThemeError as exc:
        assert exc.message == "unknown pack"
    else:
        raise AssertionError("unknown pack should fail")

    save_staff(conn, "admin", "secret-pass", "admin")
    login = client.post(
        "/admin/login",
        data={"username": "admin", "password": "secret-pass"},
        follow_redirects=False,
    )
    assert login.status_code == 303
    client.cookies.update(login.cookies)

    import shop.app as shop_app

    previous_countries = shop_app.country_choices
    shop_app.country_choices = lambda: [("US", "United States")]
    try:
        page = client.get("/admin/appearance")
    finally:
        shop_app.country_choices = previous_countries
    assert page.status_code == 200
    assert "Coral Market" in page.text
    assert 'name="pack" value="coral-market"' in page.text

    bad = client.post("/admin/appearance", data={"pack": "nope"}, follow_redirects=False)
    assert bad.status_code == 303
    assert "theme_bad" in bad.headers["location"]
    assert client.get("/api/buyer-theme").json()["activeId"] == "coral-market"

    ok = client.post(
        "/admin/appearance",
        data={"pack": "coral-market"},
        follow_redirects=False,
    )
    assert ok.status_code == 303
    assert "theme_saved" in ok.headers["location"]
    stored = conn.execute(
        "select value from settings where key = 'buyer_theme'"
    ).fetchone()["value"]
    assert stored == "coral-market"


def test_web_stylesheet_defaults_match_the_pack():
    client = TestClient(create_app(units_per_usd=1, db_path=":memory:"))
    tokens = client.get("/api/buyer-theme").json()["pack"]
    css = (ROOT / "harbor-web/src/styles/theme.scss").read_text()
    mapping = {
        "color.primary": "--hb-primary",
        "color.primarySoft": "--hb-primary-soft",
        "color.page": "--hb-page",
        "color.ink": "--hb-ink",
        "color.muted": "--hb-muted",
        "color.onPrimary": "--hb-on-primary",
        "color.surface": "--hb-surface",
        "color.sale": "--hb-sale",
        "color.badge": "--hb-badge",
    }
    for key, var in mapping.items():
        assert f"{var}: {tokens['tokens'][key]}" in css
    for key, var in {
        "color.primaryHover": "--hb-primary-hover",
        "color.primaryPressed": "--hb-primary-pressed",
        "color.primaryDisabled": "--hb-primary-disabled",
    }.items():
        assert f"{var}: {tokens['derived'][key]}" in css
    # The stylesheet must not drift from the documented contract keys.
    doc = (ROOT / "docs/buyer-theme.md").read_text()
    for key in TOKEN_KEYS:
        assert f"`{key}`" in doc
