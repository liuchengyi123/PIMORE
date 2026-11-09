from shop.db import connect, migrate
from shop.interest import account_weights, decayed, note_click
from shop.suggest import BROWSE_SHARE, blend_order, choose, diverse_order, fit_add, for_you, gap, ranked_for_you, visit_window


def test_goals_advance_one_threshold_at_a_time():
    assert gap(2000, 3900, [(3000, 400), (6000, 800)])[:3] == ("deal", 1000, 400)
    assert gap(3500, 3900, [(3000, 400), (6000, 800)])[:3] == ("ship", 400, 0)
    assert gap(4000, 3900, [(3000, 400), (6000, 800)])[:3] == ("deal", 2000, 800)
    assert gap(7000, 3900, [(3000, 400), (6000, 800)])[0] == "done"


def test_home_picks_follow_the_categories_they_open_most():
    items = [
        {"sku": f"k{i}", "category": "kitchen", "stock": 1, "price_cents": 100}
        for i in range(6)
    ] + [
        {"sku": f"c{i}", "category": "cleaning", "stock": 1, "price_cents": 100}
        for i in range(6)
    ]
    picked = for_you(items, taste={"kitchen": 5, "cleaning": 1})
    assert picked
    assert sum(item["category"] == "kitchen" for item in picked) > sum(
        item["category"] == "cleaning" for item in picked
    )
    assert for_you(items) == []


def test_newer_click_outranks_an_older_one():
    weights = decayed([("just-viewed", 1), ("added-earlier", 3)])
    assert weights["just-viewed"] > weights["added-earlier"]


def test_account_clicks_keep_the_latest_first():
    conn = connect(":memory:")
    migrate(conn)
    note_click(conn, "a@shop.test", "old", 3)
    note_click(conn, "a@shop.test", "new", 1)
    weights = account_weights(conn, "a@shop.test")
    assert list(weights)[0] == "new"
    assert weights["new"] > weights["old"]
    assert account_weights(conn, "") == {}


def test_home_picks_follow_the_price_of_products_they_open():
    items = [
        {"sku": f"cheap-{i}", "category": "kitchen", "stock": 1, "price_cents": 200 + i}
        for i in range(12)
    ] + [
        {"sku": f"dear-{i}", "category": "kitchen", "stock": 1, "price_cents": 8000 + i}
        for i in range(12)
    ]
    picked = for_you(items, {"cheap-0": 6})
    assert picked
    assert all(item["price_cents"] < 1000 for item in picked)


def test_one_tap_add_stays_inside_the_gap_and_the_same_category():
    items = [
        {"sku": "tiny", "category": "kitchen", "price_cents": 200},
        {"sku": "cover", "category": "kitchen", "price_cents": 5000},
        {"sku": "other", "category": "desk", "price_cents": 1800},
        {"sku": "near", "category": "kitchen", "price_cents": 1700},
    ]
    picked = fit_add(items, {"kitchen"}, 1900)
    assert picked["sku"] == "near"
    assert fit_add(items, {"kitchen"}, 100) is None


def test_cart_bar_talks_about_shipping_not_the_coupon():
    from fastapi.testclient import TestClient

    from shop.app import create_app

    client = TestClient(create_app(units_per_usd=100, db_path=":memory:"))
    page = client.get("/cart", cookies={"cart": "toy-ball:1"})
    assert "Checkout now pays" in page.text
    assert "Add {amount} to save" not in page.text
    assert "to save" not in page.text


def test_checkout_addons_prefer_prices_that_close_the_gap():
    items = [
        {"sku": "cheap", "category": "kitchen", "stock": 1, "price_cents": 200},
        {"sku": "fit", "category": "desk", "stock": 1, "price_cents": 1800},
        {"sku": "over", "category": "kitchen", "stock": 1, "price_cents": 5000},
        {"sku": "held", "category": "kitchen", "stock": 1, "price_cents": 900},
    ]
    picked = choose(
        items,
        exclude={"held"},
        anchors=[{"category": "kitchen"}],
        budget=1900,
        limit=2,
    )
    assert [item["sku"] for item in picked][0] == "fit"
    assert "held" not in [item["sku"] for item in picked]


def _shelf():
    items = []
    for cat in ["personal", "kitchen", "cleaning", "storage", "pet"]:
        for i in range(8):
            items.append(
                {
                    "sku": f"{cat}-{i}",
                    "category": cat,
                    "stock": 1,
                    "price_cents": 500 + i,
                    "image_url": "x",
                }
            )
    return items


def test_diverse_order_spreads_categories():
    picked = diverse_order(_shelf(), salt=9, limit=10)
    cats = {item["category"] for item in picked}
    assert len(cats) >= 4


def test_blend_order_keeps_browse_share():
    items = _shelf()
    interest = {"personal-0": 10, "personal-1": 8}
    ordered = blend_order(items, interest=interest, catalog=items, salt=4, browse_share=0.4)
    first = ordered[:10]
    personal = sum(1 for item in first if item["category"] == "personal")
    assert 2 <= personal <= 5
    assert len({item["category"] for item in first}) >= 3



def test_ranked_for_you_caps_browse_category_share():
    items = _shelf()
    interest = {"personal-0": 12, "personal-1": 9, "personal-2": 7}
    picked = ranked_for_you(items, interest, limit=12, salt=11, browse_share=0.4)
    assert len(picked) == 12
    personal = sum(1 for item in picked if item["category"] == "personal")
    assert personal <= 5
    assert len({item["category"] for item in picked}) >= 3


def test_blend_order_first_page_near_browse_share():
    items = _shelf()
    interest = {"kitchen-0": 10, "kitchen-1": 8, "kitchen-2": 6}
    ordered = blend_order(items, interest=interest, catalog=items, salt=7, browse_share=BROWSE_SHARE)
    first = ordered[:12]
    kitchen = sum(1 for item in first if item["category"] == "kitchen")
    assert kitchen <= 5
    assert len({item["category"] for item in first}) >= 3


def test_home_rails_can_be_mutually_exclusive():
    """Mirrors home(): shop / feed / foryou use exclude + different salts."""
    items = _shelf()
    interest = {"personal-0": 10, "cleaning-0": 4}
    shop = diverse_order(items, salt=0x11111111, limit=12)
    shop_skus = {item["sku"] for item in shop}
    feed = blend_order(
        items,
        interest=interest,
        catalog=items,
        salt=3,
        browse_share=0.4,
        exclude=shop_skus,
    )[:12]
    feed_skus = {item["sku"] for item in feed}
    featured = diverse_order(
        items,
        salt=0x22222222,
        exclude=shop_skus | feed_skus,
        limit=8,
    )
    featured_skus = {item["sku"] for item in featured}
    you = ranked_for_you(
        items,
        interest,
        limit=12,
        salt=0x33333333,
        browse_share=0.4,
        exclude=shop_skus | feed_skus | featured_skus,
    )
    assert shop_skus.isdisjoint(feed_skus)
    assert shop_skus.isdisjoint({item["sku"] for item in featured})
    assert feed_skus.isdisjoint({item["sku"] for item in featured})
    you_skus = {item["sku"] for item in you}
    assert you_skus.isdisjoint(shop_skus)
    assert you_skus.isdisjoint(feed_skus)
    # Featured may be re-opened only if catalog too small; with 40 SKUs keep exclusive.
    assert you_skus.isdisjoint(featured_skus)


def test_held_back_item_stays_behind_even_when_it_is_hot():
    items = [
        {"sku": "plain", "category": "tableware", "stock": 1, "price_cents": 200},
        {"sku": "sticks", "category": "tableware", "stock": 1, "price_cents": 72},
    ]
    ordered = diverse_order(
        items,
        salt=3,
        heat={"plain": 0, "sticks": 9000},
        prior={"plain": 0, "sticks": 1},
        heat_unit=98,
    )
    assert [item["sku"] for item in ordered] == ["plain", "sticks"]


def test_each_visit_opens_on_a_different_pushed_item():
    items = [{"sku": f"p{i}", "category": "kitchen", "stock": 1} for i in range(30)]
    items.append({"sku": "sticks", "category": "kitchen", "stock": 1})
    prior = {item["sku"]: (1 if item["sku"] == "sticks" else 0) for item in items}
    first = [item["sku"] for item in visit_window(items, salt=1, prior=prior)]
    second = [item["sku"] for item in visit_window(items, salt=2, prior=prior)]
    assert first[0] != second[0]
    assert first[-1] == "sticks"
    assert second[-1] == "sticks"
    assert "sticks" not in first[:20]
