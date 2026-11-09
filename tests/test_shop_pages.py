import pytest
from fastapi.testclient import TestClient

from shop.app import create_app
from shop.pricing import quote

BUYER = [
    "/",
    "/c/kitchen",
    "/search?q=rack",
    "/p/drain-rack",
    "/cart",
    "/checkout",
    "/payment",
    "/orders/1",
    "/login",
    "/account/password",
    "/reset-password",
    "/account/orders",
    "/account/coupons",
    "/account/balance",
    "/account/withdraw",
    "/share",
    "/check-in",
    "/policies/shipping",
    "/policies/privacy",
    "/contact",
]

ADMIN = [
    "/admin/stats",
    "/admin/orders",
    "/admin/orders/1",
    "/admin/withdrawals",
    "/admin/promos",
    "/admin/campaigns",
    "/admin/coupons",
    "/admin/products",
    "/admin/ads",
]


@pytest.fixture()
def client():
    return TestClient(create_app(units_per_usd=150, db_path=":memory:"))


def test_third_level_narrows_a_department(client):
    page = client.get("/c/kitchen")
    assert page.status_code == 200
    assert "Utensils" in page.text
    assert "/c/kitchen/gadgets?country=US" in page.text
    narrowed = client.get("/c/kitchen/gadgets")
    assert "Silicone spatula" in narrowed.text
    assert "Dish rack" not in narrowed.text
    assert client.get("/c/kitchen/no-such").status_code == 404
    spanish = client.get("/c/kitchen?country=ES")
    assert "Utensilios" in spanish.text
    home = client.get("/")
    assert "/static/dept/kitchen.svg" in home.text
    assert "/categories?country=US" in home.text
    assert "/static/dept/party.svg" not in home.text
    index = client.get("/categories")
    assert index.status_code == 200
    assert "/static/dept/party.svg" in index.text
    assert "Paper and care" in index.text


def test_home_japan_shows_yen_for_dish_rack(client):
    page = client.get("/?country=JP")
    assert page.status_code == 200
    assert "検索" in page.text
    assert "キッチン" in page.text
    assert "1,800円" in page.text
    assert "水切りラック" in page.text
    assert "¥" not in page.text
    assert "product-grid" in page.text
    assert "/static/dept/kitchen.svg" in page.text
    assert "Schibsted+Grotesk" in page.text
    assert "Noto+Sans+JP" in page.text


def test_a_price_change_is_visible_on_the_next_open(client):
    assert "$12.00" in client.get("/?country=US").text
    client.app.state.db.execute("update products set price_cents = 2500 where sku = 'drain-rack'")
    client.app.state.cache.delete("shop:catalog")
    client.app.state.cache.delete("shop:catalog-index")
    page = client.get("/?country=US")
    assert "$25.00" in page.text


def test_home_germany_shows_euro(client):
    page = client.get("/?country=DE")
    assert "Suchen" in page.text
    assert "Küche" in page.text
    assert "€1,800.00" in page.text
    assert "Geschirrständer" in page.text


def test_employee_logs_in_with_a_separate_account(client):
    from shop.staff import save_staff

    save_staff(client.app.state.db, "admin", "secret-pass", "admin")
    entered = client.post(
        "/admin/login",
        data={"username": "admin", "password": "secret-pass"},
        follow_redirects=False,
    )
    assert entered.status_code == 303
    created = client.post(
        "/admin/staff",
        data={"username": "mina", "password": "employee1", "role": "staff"},
        follow_redirects=False,
    )
    assert created.status_code == 303
    signed = client.post(
        "/admin/login",
        data={"username": "mina", "password": "employee1"},
        follow_redirects=False,
    )
    assert signed.status_code == 303
    page = client.get("/admin/orders")
    assert page.status_code == 200
    assert "mina" in page.text
    assert 'class="shell"' in page.text
    blocked = client.post(
        "/admin/staff",
        data={"username": "other", "password": "employee2", "role": "admin"},
        follow_redirects=False,
    )
    assert blocked.status_code == 403


def test_admin_login_is_chinese(client):
    page = client.get("/admin/login")
    assert "管理员登录" in page.text
    assert "账号" in page.text
    assert "密码" in page.text
    assert "Search" not in page.text


def test_missing_geo_database_uses_united_states(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "Search" in page.text
    assert "$12.00" in page.text
    assert "検索" not in page.text
    assert "Noto+Sans+JP" not in page.text


def test_home_keeps_later_products_off_the_first_screen(client):
    db = client.app.state.db
    for index in range(30):
        db.execute(
            """
            insert into products
                (sku, category, price_cents, stock, names, bullets, description, specs, image_url, published)
            values (?, 'kitchen', 500, 3, ?, '{}', ?, '{}', '', 1)
            """,
            (f"extra-{index}", '{"en":"Extra later"}', '{"en":"Extra later"}'),
        )
    client.app.state.cache.delete("shop:catalog")
    page = client.get("/")
    assert "extra-29" not in page.text
    assert page.text.count('class="card"') < 80


def test_product_has_buy_box_and_no_stars_without_reviews(client):
    page = client.get("/p/drain-rack?country=JP")
    assert page.status_code == 200
    assert "crumbs" in page.text
    assert 'class="buy-actions"' in page.text
    assert page.text.count('class="advantage"') == 4
    assert "仕様" in page.text
    for mark in ("★", "☆", "⭐"):
        assert mark not in page.text


def test_listing_exposes_sort_and_filters(client):
    page = client.get("/c/kitchen?country=US&sort=price_asc&min=1&max=20")
    assert page.status_code == 200
    for value in ("featured", "price_asc", "price_desc", "newest"):
        assert f'value="{value}"' in page.text
    assert 'name="category"' in page.text
    assert 'name="min"' in page.text
    search = client.get("/search?country=US&q=rack&sort=newest")
    assert search.status_code == 200
    assert "Dish rack" in search.text
    spanish = client.get("/search?country=US&lang=en&q=Escurridor")
    assert "Dish rack" in spanish.text
    assert "Escurridor de platos" not in spanish.text
    japanese = client.get("/search?country=US&lang=en&q=水切りラック")
    assert "Dish rack" in japanese.text


def test_checkout_amount_matches_quote_and_has_no_ad_slot(client):
    expected = quote(
        merchandise_cents=0,
        tiers=[(3000, 400), (6000, 800)],
        coupon_cents=0,
        coupon_threshold_cents=0,
        free_shipping_cents=3900,
        shipping_cents=700,
        balance_cents=0,
        use_balance=False,
        units_per_usd=150,
        minor_units=0,
    )
    page = client.get("/checkout?country=JP")
    assert page.status_code == 200
    assert f'data-due-local="{expected.due_local}"' in page.text
    assert "data-ad" not in page.text
    for word in ("VAT", "Sales tax", "MwSt", "消費税"):
        assert word not in page.text
    payment = client.get("/payment?country=JP")
    assert payment.status_code == 200
    assert "data-ad" not in payment.text


def test_buyer_pages_open_and_admin_requires_password(client):
    for path in BUYER:
        response = client.get(path)
        assert response.status_code == 200, path
    assert client.get("/admin/login").status_code == 200
    for path in ADMIN:
        assert client.get(path).status_code == 401, path
    missing = client.get("/no-such-page")
    assert missing.status_code == 404
    assert "Page not found" in missing.text


def test_english_heat_label_and_single_locale_pill(client):
    from shop.i18n import UI, heat_line
    from shop.mobile_api import _interest

    page = client.get("/c/kitchen?country=CN&lang=en")
    assert page.status_code == 200
    assert "Interest · " in page.text
    assert "关注热度" not in page.text
    assert page.text.count('class="fn-locale-pill"') == 1
    assert 'class="fn-locale-pill">CN · CNY<' in page.text
    assert "US · USD" not in page.text
    assert ">English</option>" in page.text
    assert ">CN · CNY</option>" not in page.text
    home = client.get("/?country=CN&lang=en")
    assert "关注热度" not in home.text
    assert "Interest · " in home.text
    assert home.text.count('class="fn-locale-pill"') == 1
    zh = client.get("/c/kitchen?country=CN&lang=zh")
    assert "关注热度 · " in zh.text
    assert "Interest ·" not in zh.text
    assert 'class="fn-locale-pill">CN · CNY<' in zh.text
    product = client.get("/p/drain-rack?country=CN&lang=en")
    assert "关注热度" not in product.text
    assert 'data-tpl="Watching heat {n}"' in product.text
    assert heat_line(UI["en"], 12) == "Interest · 12"
    assert heat_line(UI["zh"], 12) == "关注热度 · 12"
    assert heat_line(UI["zh-Hant"], 4) == "關注熱度 · 4"
    assert _interest({"heat": 15, "stock": 20}, UI["ja"]) == "注目度 · 15"
    assert "关注" not in _interest({"heat": 15, "stock": 20}, UI["en"])
    for code in ("en", "es", "de", "fr", "pt", "ja", "zh", "zh-Hant"):
        assert "{n}" in UI[code]["heat_label"]
        if not code.startswith("zh"):
            rendered = heat_line(UI[code], 8)
            assert "关注" not in rendered
            assert "有人" not in rendered


def test_zh_mobile_chrome_follows_locale(client):
    """H5 home, Me, and the bottom tab follow 中文; English storefront stays English."""
    from shop.i18n import UI

    zh_home = client.get("/?country=CN&lang=zh").text
    for text in (
        "搜索厨房、收纳、清洁",
        "本周",
        "厨房焕新 · 最高省 30%",
        "去逛逛 →",
        "特卖",
        "新品",
        "闪购",
        "优惠券",
        "签到",
        "余额",
        "邀请",
        "愿望单",
        "订单",
        "帮助",
        "为你推荐",
        "厨房",
        "清洁",
        "收纳",
        "宠物",
        "洗护",
        "店内推荐",
        ">我的<",
        'data-lucky-off="{pct}% 优惠"',
        ">10% 优惠<",
    ):
        assert text in zh_home, text
    for text in (
        "Search kitchen, storage, cleaning",
        "THIS WEEK",
        "Kitchen refresh",
        "Shop →",
        ">For you<",
        ">Bath<",
        ">In the shop<",
        ">Me<",
        'data-lucky-off="{pct}% OFF"',
    ):
        assert text not in zh_home, text

    en_home = client.get("/?country=US&lang=en").text
    for text in (
        "Search kitchen, storage, cleaning",
        "THIS WEEK",
        "Kitchen refresh · up to 30% off",
        "Shop →",
        ">For you<",
        ">Bath<",
        ">In the shop<",
        ">Me<",
        'data-lucky-off="{pct}% OFF"',
        ">10% OFF<",
    ):
        assert text in en_home, text
    assert "搜索厨房" not in en_home
    assert "店内推荐" not in en_home

    zh_me = client.get("/account?country=CN&lang=zh").text
    assert "游客" in zh_me
    assert "支持游客下单" in zh_me
    assert "欢迎来到 Harbor" in zh_me
    assert "登录后同步订单与愿望单" in zh_me
    assert ">全部<" in zh_me or ">全部 ›<" in zh_me or "全部 ›" in zh_me
    assert ">我的<" in zh_me
    assert "Guest checkout available" not in zh_me
    assert "Welcome to Harbor" not in zh_me
    css = client.get("/static/fn-mobile.min.css").text
    assert "body.fn-acc-page .fn-acc-welcome .fn-acc-sub" in css
    assert "#64748b" in css

    assert UI["zh"]["me"] == "我的"
    assert UI["zh-Hant"]["me"] == "我的"
    assert UI["zh-Hant"]["m_flash"] == "閃購"
    assert UI["en"]["me"] == "Me"
    assert UI["es"]["guest_checkout"] == "Guest checkout available"
    assert UI["ja"]["lucky_chip"] == "{pct}% OFF"


def _home_feed_skus(html):
    import re
    chunk = html.split('class="m01-grid"', 1)[-1].split("m01-more", 1)[0]
    return re.findall(r'href="/p/([^"?]+)', chunk)


def test_home_list_stays_until_reload(client):
    first = client.get("/")
    assert first.status_code == 200
    mix = first.cookies.get("home_mix")
    assert mix
    assert "private, no-cache" in first.headers.get("cache-control", "")
    assert 'nav.type !== "reload"' in first.text
    client.get("/p/drain-rack")
    client.get("/c/kitchen")
    second = client.get("/", headers={"Cache-Control": "max-age=0"})
    assert client.cookies.get("home_mix") == mix
    assert _home_feed_skus(first.text) == _home_feed_skus(second.text)
    assert _home_feed_skus(first.text)
    refreshed = client.get("/?fresh=1", follow_redirects=False)
    assert refreshed.status_code == 302
    assert refreshed.headers["location"] == "/"
    assert refreshed.cookies.get("home_mix")
    assert refreshed.cookies.get("home_mix") != mix
    landed = client.get("/")
    assert client.cookies.get("home_mix") == refreshed.cookies.get("home_mix")
    assert "fresh=" not in str(landed.url)


def test_visual_rules_in_stylesheet(client):
    css = client.get("/static/shop.css").text
    assert "font-size: 16px" in css
    assert "min-height: 44px" in css
    assert "#ffffff" in css
    assert "#141414" in css


def _coupon_names(html):
    import re

    rows = re.findall(r'<article class="fn-coupon-row">.*?</article>', html, re.S)
    return [re.search(r'class="nm">([^<]+)', row).group(1).strip() for row in rows]


def test_wallet_hides_unearned_catalog_templates():
    from shop.checkout import wallet_visible

    assert wallet_visible("public", 1, "", 0, set()) is False
    assert wallet_visible("first", 2, "", 0, set()) is False
    assert wallet_visible("share", 3, "", 0, set()) is False
    assert wallet_visible("public", 1, "a@b.c", 0, set()) is True
    assert wallet_visible("first", 2, "a@b.c", 0, set()) is True
    assert wallet_visible("first", 2, "a@b.c", 1, {2}) is False
    assert wallet_visible("share", 3, "a@b.c", 0, set()) is False
    assert wallet_visible("checkin", 4, "a@b.c", 0, set()) is False
    assert wallet_visible("desktop", 5, "a@b.c", 0, set()) is False
    assert wallet_visible("share", 3, "a@b.c", 2, {3}) is True
    assert wallet_visible("checkin", 4, "a@b.c", 2, {4}) is True


def test_guest_me_does_not_list_the_coupon_catalog(client):
    from shop.checkout import list_coupons

    me = client.get("/account?country=US")
    assert me.status_code == 200
    assert 'data-coupon-count="0"' in me.text
    assert "lucky-chip" in me.text
    coupons = client.get("/account/coupons?country=US")
    assert coupons.status_code == 200
    assert _coupon_names(coupons.text) == []
    assert "Sign in to see coupons on your account." in coupons.text
    assert "Storewide saving is the 10% OFF spin." in coupons.text
    assert 'class="fn-coupon-lead"' in coupons.text
    assert 'href="/login?next=/account/coupons&amp;country=US"' in coupons.text
    css = client.get("/static/fn-mobile.min.css").text
    lead = css[css.find(".fn-coupon-lead"):css.find(".fn-coupon-lead") + 700]
    assert "color:#0F2744" in lead
    assert "font-size:15px" in lead
    assert "font-weight:600" in lead
    assert "line-height:1.35" in lead
    assert "rgba(255,255,255,.75)" not in lead
    assert "lucky-chip" in coupons.text
    zh = client.get("/account/coupons?country=CN&lang=zh")
    assert _coupon_names(zh.text) == []
    assert "登录后查看账户里的优惠券。" in zh.text
    assert "全场优惠是幸运转盘的 10% OFF。" in zh.text
    assert "首单优惠" not in zh.text
    assert "可直接使用" not in zh.text
    assert "分享奖励" not in zh.text
    check = client.get("/check-in?country=US")
    assert check.text.count("$1.00") >= 7
    share = client.get("/share?country=US")
    assert share.text.count("$4.00") >= 2
    kinds = {row["kind"] for row in list_coupons(client.app.state.db, "", 10_000)}
    assert {"public", "first"} <= kinds
    assert kinds.isdisjoint({"share", "desktop", "checkin"})
    stored = [
        row["kind"]
        for row in client.app.state.db.execute(
            "select kind from coupons where enabled = 1 order by id"
        ).fetchall()
    ]
    assert stored == ["public", "first", "share", "desktop", "checkin"]


def test_signed_in_wallet_counts_owned_coupons_only(client):
    created = client.post(
        "/register",
        data={"email": "new@example.com", "password": "correct horse", "next": "/account"},
    )
    assert created.status_code == 200
    assert 'data-coupon-count="2"' in created.text
    coupons = client.get("/account/coupons?country=US")
    assert _coupon_names(coupons.text) == ["First order", "Ready to use"]
    db = client.app.state.db
    db.execute(
        """
        insert into orders (submit_id, email, status, currency, units_per_usd, due_cents, due_local)
        values ('wallet-order', 'new@example.com', 'cancelled', 'USD', 1, 100, 100)
        """
    )
    db.commit()
    still = client.get("/account?country=US")
    assert 'data-coupon-count="2"' in still.text
    db.execute("update orders set status = 'paid' where submit_id = 'wallet-order'")
    db.commit()
    after = client.get("/account/coupons?country=US")
    assert _coupon_names(after.text) == ["Ready to use"]
    assert 'data-coupon-count="1"' in client.get("/account?country=US").text
    stamped = client.post("/check-in", follow_redirects=False)
    assert stamped.status_code == 200
    owned = client.get("/account/coupons?country=US")
    assert _coupon_names(owned.text) == ["Daily check-in", "Ready to use"]
    assert "Share reward" not in owned.text
    assert "Home screen reward" not in owned.text
    assert 'data-coupon-count="2"' in client.get("/account?country=US").text
    db.execute("update coupons set enabled = 0 where kind in ('public', 'checkin')")
    db.commit()
    empty = client.get("/account/coupons?country=US")
    assert _coupon_names(empty.text) == []
    assert "No coupons yet. Check in or share, and they show up here." in empty.text
    assert 'class="fn-coupon-lead"' in empty.text
    assert 'data-coupon-count="0"' in client.get("/account?country=US").text
