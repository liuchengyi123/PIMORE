import json

from fastapi.testclient import TestClient

from shop.app import create_app
from shop.db import connect, migrate
from shop.lp_modules import band_groups
from shop.reco import (
    DEFAULTS,
    RecoConfigError,
    browse_share_for,
    heat_points,
    load_rules,
    mix_price_bands,
    normalize,
    personal_signals,
    related_hot_points,
    save_rules,
    select_lp_rows,
)
from shop.staff import save_staff
from shop.suggest import diverse_order


def _row(sku, cents, clicks=0, sub="", category="kitchen", image=""):
    return {
        "sku": sku,
        "category": category,
        "subcategory": sub,
        "price_cents": cents,
        "stock": 4,
        "published": 1,
        "image_url": image,
        "clicks": clicks,
    }


def _rules(**overrides):
    raw = dict(DEFAULTS)
    raw.update(overrides)
    return normalize(raw)


def _clicks(rows):
    return {row["sku"]: int(row.get("clicks") or 0) for row in rows}


def test_heat_is_clicks_times_the_multiplier():
    assert heat_points(1, 98) == 98
    assert heat_points(2, 98) == 196
    assert heat_points(0, 98) == 0
    assert heat_points(3, 10) == 30
    assert heat_points(-1, 98) == 0


def test_checkbox_wins_over_the_hidden_zero():
    from shop.reco import parse_form

    rules = parse_form({"lp_shuffle": ["0", "1"], "hot_boost": "0", "heat_per_click": "98"})
    assert rules["lp_shuffle"] == 1
    assert rules["hot_boost"] == 0
    assert rules["heat_per_click"] == 98


def test_rules_reject_a_cheap_wall_quota_that_does_not_fit():
    try:
        normalize({"lp_max_cards": 10, "lp_band_3_5_min": 8, "lp_band_5_10_min": 8})
    except RecoConfigError as exc:
        assert "不能大于" in exc.message
    else:
        raise AssertionError("expected quota error")
    saved = normalize({"heat_per_click": "98", "browse_share": "0.4", "lp_shuffle": "1"})
    assert saved["heat_per_click"] == 98
    assert saved["browse_share"] == 0.4


def test_lp_does_not_sort_by_price_and_one_click_beats_jitter():
    rows = [
        _row("cheap", 150, clicks=0),
        _row("mid", 400, clicks=5),
        _row("high", 800, clicks=0),
    ]
    rules = _rules(lp_max_cards=4, lp_under3_cap=4, lp_band_3_5_min=0, lp_band_5_10_min=0, lp_shuffle=0)
    picked = select_lp_rows(rows, clicks=_clicks(rows), salt=1, rules=rules)
    prices = [row["price_cents"] for row in picked]
    assert prices != sorted(prices)
    assert [row["sku"] for row in picked][0] == "mid"
    rules["lp_shuffle"] = 1
    for salt in range(8):
        shaken = select_lp_rows(rows, clicks=_clicks(rows), salt=salt, rules=rules)
        assert shaken[0]["sku"] == "mid"


def test_price_band_quotas_cap_the_cheapest_band():
    rows = [_row(f"a{i:02d}", 150) for i in range(10)]
    rows += [_row(f"m{i:02d}", 400) for i in range(8)]
    rows += [_row(f"h{i:02d}", 800) for i in range(8)]
    rules = _rules(lp_shuffle=0, lp_sub_cap=0)
    picked = select_lp_rows(rows, clicks={}, salt=0, rules=rules)
    under = [row for row in picked if row["price_cents"] < 300]
    mid = [row for row in picked if 300 <= row["price_cents"] < 500]
    high = [row for row in picked if 500 <= row["price_cents"] <= 1000]
    assert len(under) <= rules["lp_under3_cap"]
    assert len(mid) >= rules["lp_band_3_5_min"]
    assert len(high) >= rules["lp_band_5_10_min"]
    assert len(picked) <= rules["lp_max_cards"]


def test_subcategory_cap_holds_while_other_subs_can_fill():
    rows = [_row(f"g{i}", 450, clicks=9, sub="gadgets") for i in range(8)]
    rows += [_row(f"o{i}", 450, clicks=0, sub=f"other{i}") for i in range(8)]
    rules = _rules(
        lp_max_cards=8,
        lp_under3_cap=8,
        lp_band_3_5_min=0,
        lp_band_5_10_min=0,
        lp_sub_cap=2,
        lp_shuffle=0,
    )
    picked = select_lp_rows(rows, clicks=_clicks(rows), salt=3, rules=rules)
    assert sum(1 for row in picked if row["subcategory"] == "gadgets") == 2
    assert len(picked) == 8


def test_hero_prefers_a_mid_band_photo_over_a_hotter_edge_price():
    rows = [
        _row("tail", 900, clicks=10, image="/a.jpg"),
        _row("plain", 400, clicks=4),
        _row("photo", 600, clicks=0, image="/b.jpg"),
    ]
    rules = _rules(lp_max_cards=4, lp_under3_cap=4, lp_band_3_5_min=0, lp_band_5_10_min=0, lp_shuffle=0)
    picked = select_lp_rows(rows, clicks=_clicks(rows), salt=0, rules=rules)
    assert picked[0]["sku"] == "photo"


def test_hot_list_boost_is_a_cold_start_tie_break_not_the_click_score():
    rows = [
        _row("aaa", 150, category="kitchen"),
        _row("zzz", 950, category="kitchen"),
        _row("sib", 950, category="kitchen"),
        _row("other", 950, category="cleaning"),
    ]
    titles = {"zzz": 2}
    on = _rules(lp_shuffle=0, lp_max_cards=4, lp_under3_cap=4, lp_band_3_5_min=0, lp_band_5_10_min=0, hot_boost=1, hot_weight=12)
    picked = select_lp_rows(rows, clicks={}, title_scores=titles, salt=0, rules=on)
    assert picked[0]["sku"] == "zzz"
    off = dict(on)
    off["hot_boost"] = 0
    cold = select_lp_rows(rows, clicks={}, title_scores=titles, salt=0, rules=off)
    assert cold[0]["sku"] == "aaa"
    points = related_hot_points(rows, titles, enabled=True, weight=12)
    assert points["zzz"] == 24
    assert points["sib"] == 4.2
    assert "other" not in points
    # One real click (98) still outranks a title match of 24.
    clicked = select_lp_rows(
        rows,
        clicks={"aaa": 1},
        title_scores=titles,
        salt=0,
        rules=on,
    )
    assert clicked[0]["sku"] == "aaa"


def test_deals_mix_does_not_become_a_cheap_wall():
    rows = [_row(f"c{i}", 120, clicks=20) for i in range(10)]
    rows += [_row(f"d{i}", 500, clicks=0) for i in range(4)]
    picked = mix_price_bands(
        rows,
        {row["sku"]: row["clicks"] * 98 for row in rows},
        limit=6,
        under_cents=300,
        under_cap=2,
        salt=1,
        heat_unit=98,
        shuffle=False,
    )
    assert sum(1 for row in picked if row["price_cents"] < 300) <= 2
    assert any(row["price_cents"] >= 300 for row in picked)


def test_personal_slots_stay_off_until_the_signal_minimum():
    rules = _rules(personal_min_signals=3, browse_share=0.4)
    assert personal_signals({"just-one": 14, "crumb": 0.15}) == 1
    assert browse_share_for({"just-one": 14, "crumb": 0.15}, None, rules) == 0
    warm = {"a": 2, "b": 1, "c": 4}
    assert personal_signals(warm, {"kitchen": 1}) == 4
    assert browse_share_for(warm, None, rules) == 0.4


def test_diverse_order_uses_click_heat_instead_of_price():
    items = [
        {"sku": "cheap", "category": "kitchen", "stock": 1, "price_cents": 100},
        {"sku": "loved", "category": "kitchen", "stock": 1, "price_cents": 900},
    ]
    picked = diverse_order(items, salt=4, heat={"cheap": 0, "loved": 196}, heat_unit=98, limit=2)
    assert picked[0]["sku"] == "loved"


def test_waterfall_bands_keep_the_incoming_order():
    groups, _overflow = band_groups(
        [
            {"sku": "dear", "price_cents": 800},
            {"sku": "cheap", "price_cents": 200},
            {"sku": "mid", "price_cents": 400},
        ]
    )
    by_id = {group["id"]: [item["sku"] for item in group["items"]] for group in groups}
    assert by_id["5_10"] == ["dear"]
    assert by_id["under_3"] == ["cheap"]
    assert by_id["3_5"] == ["mid"]


def test_settings_round_trip_and_the_product_heat_number():
    conn = connect(":memory:")
    migrate(conn)
    saved = save_rules(conn, {"heat_per_click": 50, "hot_boost": 0, "lp_shuffle": 0})
    assert saved["heat_per_click"] == 50
    assert load_rules(conn)["heat_per_click"] == 50
    assert load_rules(conn)["lp_max_cards"] == DEFAULTS["lp_max_cards"]

    client = TestClient(create_app(units_per_usd=100, db_path=":memory:"))
    db = client.app.state.db
    for visitor in ("one", "two"):
        db.execute(
            """
            insert into visits (day, kind, sku, country, lang, visitor, cents, qty)
            values ('2026-11-08', 'product', 'sink-strainer', 'US', 'en', ?, 0, 1)
            """,
            (visitor,),
        )
    body = client.get("/api/catalog/interest/sink-strainer").json()
    assert body["clicks"] == 2
    assert body["count"] == 196
    assert body["heat"] == 196
    home = client.get("/")
    assert home.status_code == 200
    assert "Interest · " in home.text
    assert "关注热度" not in home.text

    save_staff(db, "admin", "secret-pass", "admin")
    client.post("/admin/login", data={"username": "admin", "password": "secret-pass"})
    page = client.get("/admin/reco")
    assert page.status_code == 200
    assert "每次打开加多少" in page.text
    assert 'name="heat_per_click"' in page.text
    assert "千人千面" in page.text
    assert "外部热销" in page.text
    saved_form = client.post(
        "/admin/reco",
        data={
            "heat_per_click": "10",
            "lp_shuffle": "1",
            "lp_max_cards": "24",
            "lp_under3_cap": "6",
            "lp_band_3_5_min": "6",
            "lp_band_5_10_min": "6",
            "lp_sub_cap": "2",
            "browse_share": "0.25",
            "personal_min_signals": "3",
            "hot_boost": "0",
            "hot_weight": "12",
        },
        follow_redirects=False,
    )
    assert saved_form.status_code == 303
    again = client.get("/api/catalog/interest/sink-strainer").json()
    assert again["heat"] == 20
    stored = json.loads(db.execute("select value from settings where key = 'reco_rules'").fetchone()["value"])
    assert stored["browse_share"] == 0.25
    assert stored["personal_min_signals"] == 3
    assert stored["hot_boost"] == 0
    bad = client.post(
        "/admin/reco",
        data={"heat_per_click": "98", "lp_max_cards": "8", "lp_band_3_5_min": "6", "lp_band_5_10_min": "6",
              "lp_under3_cap": "2", "lp_sub_cap": "2", "browse_share": "0.4", "personal_min_signals": "1",
              "lp_shuffle": "1", "hot_boost": "1", "hot_weight": "12"},
        follow_redirects=True,
    )
    assert bad.status_code == 200
    assert "不能大于" in bad.text
