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
    assert 'lang="en"' in page.text
    assert 'data-lp-lang="en"' in page.text


def test_localized_copy_rejects_cjk_on_non_zh_markets():
    from shop.app import localized_copy

    assert localized_copy({"en": "厨房喷壶"}, "en", fallback="cjk-leak", source_zh="源中文名") == "cjk-leak"
    assert (
        localized_copy({"de": "中文标题", "en": "Glass sprayer"}, "de", fallback="cjk-leak", source_zh="源中文名")
        == "Glass sprayer"
    )
    assert localized_copy({"en": "Glass sprayer"}, "en", fallback="cjk-leak", source_zh="源中文名") == "Glass sprayer"
    assert localized_copy({"ja": "排水口ゴミ受け"}, "ja", fallback="cjk-leak", source_zh="源中文名") == "排水口ゴミ受け"
    assert localized_copy({}, "zh", fallback="cjk-leak", source_zh="源中文名") == "源中文名"
    assert localized_copy({"en": "オイル"}, "en", fallback="cjk-leak") == "cjk-leak"


def test_ad_lp_card_hides_chinese_titles_on_a_latin_market():
    import json

    client = _client()
    client.app.state.db.execute(
        """
        insert into products
            (sku, category, price_cents, stock, names, bullets, description, specs, source_zh, published)
        values ('cjk-leak', 'kitchen', 500, 8, ?, '{}', ?, '{}', ?, 1)
        """,
        (
            json.dumps({"en": "厨房喷壶", "de": "中文标题"}, ensure_ascii=False),
            json.dumps({"en": "中文描述", "de": "Eine Sprühflasche"}, ensure_ascii=False),
            "源中文名",
        ),
    )
    client.app.state.db.execute(
        """
        insert into products
            (sku, category, price_cents, stock, names, bullets, description, specs, source_zh, published)
        values ('en-ok', 'kitchen', 550, 8, ?, '{}', '{}', '{}', ?, 1)
        """,
        (
            json.dumps({"en": "Glass sprayer"}, ensure_ascii=False),
            "玻璃喷壶",
        ),
    )
    page = client.get(
        "/lp/ad/preview",
        params={"template": "dense_flash", "category": "kitchen", "skin": "kitchen", "country": "US", "preview": "1"},
        headers={"Accept-Language": "zh-CN"},
        cookies={"harbor_hl": "zh"},
    )
    assert page.status_code == 200
    assert 'data-lp-lang="en"' in page.text
    assert 'data-sku="cjk-leak"' in page.text
    assert "厨房喷壶" not in page.text
    assert "中文标题" not in page.text
    assert "中文描述" not in page.text
    assert "源中文名" not in page.text
    assert "Glass sprayer" in page.text
    assert "玻璃喷壶" not in page.text
    german = client.get(
        "/lp/ad/preview",
        params={"template": "dense_flash", "category": "kitchen", "skin": "kitchen", "country": "DE", "preview": "1"},
    )
    assert "Glass sprayer" in german.text
    assert "中文标题" not in german.text
    product = client.get("/p/cjk-leak?country=US", headers={"Accept-Language": "zh-CN"})
    assert product.status_code == 200
    assert "厨房喷壶" not in product.text
    assert "源中文名" not in product.text
    assert "cjk-leak" in product.text


def test_ui_lang_for_uses_country_unless_the_visitor_chose():
    from shop.app import ui_lang_for

    class Req:
        def __init__(self, params=None, cookies=None, headers=None):
            self.query_params = params or {}
            self.cookies = cookies or {}
            self.headers = headers or {}

    browser = Req(headers={"accept-language": "ja,zh-CN;q=0.8"})
    assert ui_lang_for(browser, "de") == "de"
    assert ui_lang_for(browser, "en") == "en"
    chosen = Req(params={"hl": "fr"}, headers={"accept-language": "ja"})
    assert ui_lang_for(chosen, "de") == "fr"
    saved = Req(cookies={"harbor_hl": "zh-Hant"}, headers={"accept-language": "en"})
    assert ui_lang_for(saved, "en") == "zh-Hant"


def test_storefront_first_visit_follows_ip_country_not_the_browser():
    client = _client()
    first = client.get("/?country=DE", headers={"Accept-Language": "ja,zh-CN;q=0.9"})
    assert first.status_code == 200
    assert 'lang="de"' in first.text
    assert 'aria-label="Suchen"' in first.text
    assert "harbor_hl" not in (first.headers.get("set-cookie") or "")
    manual = client.get("/?country=DE&lang=ja", headers={"Accept-Language": "en"})
    assert 'lang="ja"' in manual.text
    assert "harbor_hl=ja" in (manual.headers.get("set-cookie") or "")
    kept = client.get(
        "/?country=US",
        cookies={"harbor_hl": "fr"},
        headers={"Accept-Language": "de"},
    )
    assert 'lang="fr"' in kept.text
    assert 'aria-label="Rechercher"' in kept.text


def test_ad_lp_language_follows_ip_and_preview_country_only():
    from shop.i18n import UI

    client = _client()
    _login(client)
    made = client.post(
        "/admin/launch",
        data={
            "template": "dense_flash",
            "category": "kitchen",
            "skin": "kitchen",
            "platform": "meta",
            "country": "US",
        },
    )
    assert made.status_code == 200
    code = client.app.state.db.execute("select code from ad_launch_links").fetchone()["code"]
    headers = {"Accept-Language": "zh-CN,zh;q=0.9"}
    cookies = {"harbor_hl": "fr"}
    preview = client.get(
        "/lp/ad/preview",
        params={
            "template": "dense_flash",
            "category": "kitchen",
            "skin": "kitchen",
            "preview": "1",
            "country": "DE",
            "lang": "ja",
        },
        headers=headers,
        cookies=cookies,
    )
    assert preview.status_code == 200
    assert 'lang="de"' in preview.text
    assert 'data-lp-lang="de"' in preview.text
    assert "Kostenloser Versand" in preview.text
    assert "Greifen" in preview.text
    assert "Zum Shop" in preview.text
    assert "Ölsprüher" in preview.text
    assert "harbor_hl" not in (preview.headers.get("set-cookie") or "")
    assert "满" not in preview.text
    japan = client.get(
        "/lp/ad/preview",
        params={"template": "hero_headline", "category": "kitchen", "skin": "kitchen", "country": "JP"},
        headers=headers,
        cookies=cookies,
    )
    assert 'lang="ja"' in japan.text
    assert "ショップへ" in japan.text
    assert "オイルスプレー" in japan.text
    china = client.get(
        "/lp/ad/preview",
        params={"template": "countdown_grid", "category": "kitchen", "skin": "kitchen", "country": "CN"},
        headers={"Accept-Language": "en"},
        cookies={"harbor_hl": "en"},
    )
    assert 'lang="zh"' in china.text
    assert "进入店铺" in china.text
    assert "包邮" in china.text
    assert "满" not in china.text
    taiwan = client.get(
        "/lp/ad/preview",
        params={"template": "rush_flash", "category": "kitchen", "skin": "kitchen", "country": "TW"},
    )
    assert 'lang="zh-Hant"' in taiwan.text
    assert "進入店鋪" in taiwan.text
    assert "滿" not in taiwan.text
    for code_lang in ("en", "es", "pt", "de", "fr", "ja", "zh", "zh-Hant"):
        assert UI[code_lang]["lp_grab"]
        assert UI[code_lang]["lp_enter"]
        assert UI[code_lang]["lp_ship"]
        assert "{n}" in UI[code_lang]["lp_left"]


def test_saved_lp_ignores_browser_and_query_when_ip_country_is_known(monkeypatch):
    monkeypatch.setattr("shop.geo.lookup_country", lambda ip: "JP")
    client = _client()
    _login(client)
    client.post(
        "/admin/launch",
        data={"template": "dense_flash", "category": "kitchen", "skin": "kitchen", "country": "US"},
    )
    code = client.app.state.db.execute("select code from ad_launch_links").fetchone()["code"]
    saved = client.get(
        f"/lp/ad/{code}",
        params={"country": "DE", "lang": "fr"},
        headers={"Accept-Language": "de"},
        cookies={"harbor_hl": "es"},
    )
    assert 'lang="ja"' in saved.text
    assert "ショップへ" in saved.text
    assert "Kostenloser Versand" not in saved.text
    assert "harbor_hl" not in (saved.headers.get("set-cookie") or "")
    preview = client.get(
        "/lp/ad/preview",
        params={"template": "dense_flash", "category": "kitchen", "skin": "kitchen", "country": "DE", "preview": "1"},
        cookies={"harbor_hl": "es"},
        headers={"Accept-Language": "ja"},
    )
    assert 'lang="de"' in preview.text
    home = client.get("/", headers={"Accept-Language": "de"})
    assert 'lang="ja"' in home.text


def test_language_resolution_does_not_call_remote_geo():
    import time

    import httpx

    from shop.locale import resolve

    def boom(*_args, **_kwargs):
        raise AssertionError("remote geo")

    original = httpx.get
    httpx.get = boom
    try:
        client = _client()
        page = client.get(
            "/lp/ad/preview",
            params={"template": "dense_flash", "category": "kitchen", "skin": "kitchen", "country": "PT", "preview": "1"},
            headers={"Accept-Language": "ja"},
        )
        assert page.status_code == 200
        assert 'lang="pt"' in page.text
        assert "Entrar na loja" in page.text
        home = client.get("/?country=ES", headers={"Accept-Language": "en"})
        assert home.status_code == 200
        assert 'lang="es"' in home.text
    finally:
        httpx.get = original
    start = time.perf_counter()
    for _ in range(5000):
        assert resolve("DE") == ("de", "EUR")
        assert resolve("US")[0] == "en"
    assert time.perf_counter() - start < 0.1
