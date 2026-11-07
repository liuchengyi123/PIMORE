from pathlib import Path

from fastapi.testclient import TestClient

from shop.app import create_app
from shop.lp_modules import TEMPLATES, band_groups, resolve_module
from shop.staff import save_staff

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_MARK = {
    "dense_flash": "lp-dense",
    "hero_headline": "lp-headline",
    "countdown_grid": "lp-count-top",
    "price_waterfall": "lp-waterfall",
    "rush_flash": "lp-rush",
}


def _client():
    return TestClient(create_app(units_per_usd=150, db_path=":memory:"))


def _login(client):
    save_staff(client.app.state.db, "admin", "secret-pass", "admin")
    entered = client.post(
        "/admin/login",
        data={"username": "admin", "password": "secret-pass"},
        follow_redirects=False,
    )
    assert entered.status_code == 303


def _funnel_lands(db):
    try:
        return db.execute(
            "select extra from ad_funnel where kind = 'land'"
        ).fetchall()
    except Exception:
        return []


def test_registry_maps_five_templates_to_partials():
    assert [row["id"] for row in TEMPLATES] == [
        "dense_flash",
        "hero_headline",
        "countdown_grid",
        "price_waterfall",
        "rush_flash",
    ]
    for row in TEMPLATES:
        assert (ROOT / "shop" / "templates" / row["partial"]).is_file()
    kitchen = resolve_module("dense_flash", "kitchen", "")
    assert kitchen["skin_id"] == "kitchen"
    assert kitchen["master"] is True
    pet = resolve_module("rush_flash", "kitchen", "pet")
    assert pet["category"] == "kitchen"
    assert pet["skin_id"] == "pet"
    assert pet["master"] is False
    groups, _overflow = band_groups(
        [
            {"sku": "a", "price_cents": 250},
            {"sku": "b", "price_cents": 400},
            {"sku": "c", "price_cents": 800},
            {"sku": "d", "price_cents": 1500},
        ]
    )
    assert [group["id"] for group in groups] == ["under_3", "3_5", "5_10"]
    assert groups[0]["items"][0]["sku"] == "a"


def test_admin_launch_previews_the_public_renderer():
    client = _client()
    _login(client)
    page = client.get("/admin/launch")
    assert page.status_code == 200
    assert "投放落地页" in page.text
    assert 'id="lp-preview"' in page.text
    assert 'id="lp-launch-form"' in page.text
    assert 'form.addEventListener("input"' in page.text
    assert 'form.addEventListener("change"' in page.text
    assert "/lp/ad/preview?template=dense_flash&amp;category=kitchen&amp;skin=kitchen&amp;preview=1" in page.text
    for row in TEMPLATES:
        assert f'value="{row["id"]}"' in page.text
        assert row["label_zh"] in page.text
    assert "厨房" in page.text
    assert "宠物" in page.text


def test_generate_link_and_open_saved_template():
    client = _client()
    _login(client)
    before = _funnel_lands(client.app.state.db)
    preview = client.get(
        "/lp/ad/preview",
        params={
            "template": "hero_headline",
            "category": "cleaning",
            "skin": "cleaning",
            "preview": "1",
        },
    )
    assert preview.status_code == 200
    assert _funnel_lands(client.app.state.db) == before
    made = client.post(
        "/admin/launch",
        data={
            "template": "hero_headline",
            "category": "cleaning",
            "skin": "cleaning",
            "platform": "tiktok",
            "utm_source": "tiktok",
            "utm_medium": "paid",
            "utm_campaign": "clean_rush",
            "utm_content": "cleaning",
            "country": "US",
            "label": "清洁头条",
        },
    )
    assert made.status_code == 200
    assert "链接已生成" in made.text
    assert "https://linkiip.com/lp/ad/" in made.text
    assert "utm_source=tiktok" in made.text
    assert "utm_campaign=clean_rush" in made.text
    assert "template=hero_headline" in made.text
    assert "category=cleaning" in made.text
    row = client.app.state.db.execute(
        "select code, template, category, skin from ad_launch_links"
    ).fetchone()
    assert row["template"] == "hero_headline"
    assert row["category"] == "cleaning"
    assert row["skin"] == "cleaning"
    saved = client.get(f"/lp/ad/{row['code']}")
    assert saved.status_code == 200
    assert 'data-lp-template="hero_headline"' in saved.text
    assert 'data-lp-skin="cleaning"' in saved.text
    assert 'data-lp-category="cleaning"' in saved.text
    assert 'data-lp-code="' + row["code"] + '"' in saved.text
    assert "lp-headline" in saved.text
    assert "Lint roller" in saved.text
    assert "Enter the store" in saved.text
    assert "/c/cleaning?country=" in saved.text
    assert "/checkout" not in saved.text
    assert "orders over" not in saved.text.lower()
    assert "满" not in saved.text
    assert "包邮" not in saved.text
    lands = _funnel_lands(client.app.state.db)
    assert any("template=hero_headline" in (item["extra"] or "") for item in lands)
    bare = client.get(f"/lp/ad/{row['code']}")
    assert 'data-lp-template="hero_headline"' in bare.text


def test_preview_resolves_each_template_skin_and_category_pool():
    client = _client()
    for template_id, marker in TEMPLATE_MARK.items():
        page = client.get(
            "/lp/ad/preview",
            params={"template": template_id, "category": "kitchen", "skin": "kitchen", "preview": "1"},
        )
        assert page.status_code == 200
        assert f'data-lp-template="{template_id}"' in page.text
        assert 'data-lp-skin="kitchen"' in page.text
        assert 'data-lp-category="kitchen"' in page.text
        assert 'data-lp-master="1"' in page.text
        assert marker in page.text
        assert "Oil sprayer" in page.text
        assert "Dish rack" not in page.text
        assert 'class="lp-grab"' in page.text
        assert "/api/ad/deal?sku=" in page.text
        assert "to=/p/" in page.text
        assert "/checkout" not in page.text
        assert "Enter the store" in page.text
        assert "/c/kitchen?country=" in page.text
        assert "Free shipping" in page.text
        assert "orders over" not in page.text.lower()
        assert "满" not in page.text
        assert "包邮" not in page.text
    hero = client.get(
        "/lp/ad/preview",
        params={"template": "hero_headline", "category": "kitchen", "skin": "kitchen"},
    )
    assert 'data-lp-hero="sink-strainer"' in hero.text
    waterfall = client.get(
        "/lp/ad/preview",
        params={"template": "price_waterfall", "category": "kitchen", "skin": "kitchen"},
    )
    assert 'data-band="3_5"' in waterfall.text
    assert 'data-band="5_10"' in waterfall.text
    dyed = client.get(
        "/lp/ad/preview",
        params={"template": "dense_flash", "category": "kitchen", "skin": "pet"},
    )
    assert 'data-lp-skin="pet"' in dyed.text
    assert 'data-lp-category="kitchen"' in dyed.text
    assert 'data-lp-master="0"' in dyed.text
    assert "--accent: #C026D3" in dyed.text
    assert "Oil sprayer" in dyed.text
    assert "Toy ball" not in dyed.text
    missing = client.get("/lp/ad/preview", params={"template": "nope", "category": "kitchen"})
    assert missing.status_code == 404
    unknown = client.get("/lp/ad/deadbeef")
    assert unknown.status_code == 404
