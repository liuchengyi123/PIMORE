from fastapi.testclient import TestClient

from shop.app import create_app
from shop.campaigns import price_for
from shop.checkout import build_quote, priced_lines


def _client():
    return TestClient(create_app(units_per_usd=150, db_path=":memory:"))


def _newcomer(db):
    return db.execute(
        """
        select ci.sku, ci.price_cents, p.price_cents as regular
        from campaign_items ci
        join campaigns c on c.id = ci.campaign_id
        join products p on p.sku = ci.sku
        where c.kind = 'newcomer'
        order by ci.id
        """
    ).fetchall()


def test_admin_label_reads_the_name_inside_source_json():
    from shop.app import _product_label

    raw = '{"name":"汽车贴纸","description":"","bullets":[]}'
    assert _product_label(raw, "{}", "b7920") == "汽车贴纸"
    assert "{" not in _product_label(raw, "{}", "b7920")


def test_home_drops_the_three_tiles_and_cards_skip_the_shipping_line():
    client = _client()
    page = client.get("/")
    assert 'class="act-row"' not in page.text
    assert 'class="ship"' not in page.text


def test_admin_can_open_campaigns():
    from shop.staff import save_staff

    client = _client()
    save_staff(client.app.state.db, "admin", "secret-pass", "admin")
    entered = client.post(
        "/admin/login",
        data={"username": "admin", "password": "secret-pass"},
        follow_redirects=False,
    )
    assert entered.status_code == 303
    page = client.get("/admin/campaigns")
    assert page.status_code == 200
    assert "秒杀" in page.text
    assert "新人" in page.text
    assert "保存这场活动" in page.text
    assert "搜索商品" in page.text
    assert 'class="picker"' in page.text


def test_home_has_both_campaigns_and_inner_pages():
    client = _client()
    home = client.get("/")
    assert home.status_code == 200
    assert 'data-campaign="seckill"' in home.text
    assert 'data-campaign="new"' in home.text
    hold = _newcomer(client.app.state.db)[0]["sku"]
    assert f"/p/{hold}" in home.text
    assert 'id="pop-hold"' not in home.text
    sale = client.get("/sale")
    assert sale.status_code == 200
    assert "data-ends=" in sale.text
    assert "The price on this page lasts until the clock hits zero." in sale.text
    fresh = client.get("/new")
    assert fresh.status_code == 200
    assert 'data-live="1"' in fresh.text
    assert "One item at this price." in fresh.text


def test_one_newcomer_special_then_the_rest_return_to_regular():
    client = _client()
    rows = _newcomer(client.app.state.db)
    first, second = rows[0], rows[1]
    priced, _total = priced_lines(
        client.app.state.db,
        [{"sku": first["sku"], "qty": 1}, {"sku": second["sku"], "qty": 1}],
    )
    by_sku = {line["sku"]: line["price_cents"] for line in priced}
    assert by_sku[first["sku"]] == first["price_cents"]
    assert by_sku[second["sku"]] == second["regular"]
    alone, _total = priced_lines(client.app.state.db, [{"sku": second["sku"], "qty": 1}])
    assert alone[0]["price_cents"] == second["price_cents"]


def test_paid_account_loses_the_newcomer_price_and_block():
    client = _client()
    db = client.app.state.db
    sku = _newcomer(db)[0]["sku"]
    db.execute(
        """
        insert into orders (email, status, currency, units_per_usd, due_cents, due_local)
        values ('buyer@shop.test', 'paid', 'USD', 100, 100, 100)
        """
    )
    db.execute("insert into sessions (token, email) values ('tok', 'buyer@shop.test')")
    special, _item = price_for(db, sku, "buyer@shop.test", [{"sku": sku, "qty": 1}])
    assert special is None
    home = client.get("/", cookies={"buyer_session": "tok"})
    assert 'data-campaign="seckill"' in home.text
    assert 'data-campaign="new"' not in home.text
    page = client.get("/new", cookies={"buyer_session": "tok"})
    assert 'data-live="0"' in page.text
    product = client.get(f"/p/{sku}", cookies={"buyer_session": "tok"})
    assert product.status_code == 200


def test_gift_is_free_only_at_one_and_shipping_stays():
    client = _client()
    db = client.app.state.db
    db.execute(
        """
        insert into products
            (sku, category, price_cents, stock, names, bullets, description, specs, published)
        values ('gift-towel', 'cleaning', 120, 5, '{"en":"Towel"}', '{}', '{"en":"Towel"}', '{}', 1)
        """
    )
    one, _total = priced_lines(db, [{"sku": "gift-towel", "qty": 1}], gift_sku="gift-towel")
    assert one[0]["price_cents"] == 0
    two, _total = priced_lines(db, [{"sku": "gift-towel", "qty": 2}], gift_sku="gift-towel")
    assert two[0]["price_cents"] == 120
    promos = client.app.state.db.execute("select key, value from promos").fetchall()
    import json
    data = {row["key"]: json.loads(row["value"]) for row in promos}
    bill = build_quote(
        {"tiers": data["tiers"], "free_shipping_cents": data["free_shipping_cents"], "shipping": data["shipping"]},
        merchandise_cents=0,
        ship_country="US",
        units=100,
        currency="USD",
        minor_units=2,
    )
    assert bill.shipping_cents == 0


def test_only_one_special_price_survives_in_the_cart():
    client = _client()
    db = client.app.state.db
    rows = db.execute(
        """
        select ci.sku, ci.price_cents, p.price_cents as regular
        from campaign_items ci
        join campaigns c on c.id = ci.campaign_id
        join products p on p.sku = ci.sku
        where c.kind = 'seckill'
        order by ci.id
        limit 2
        """
    ).fetchall()
    first, second = rows
    priced, _total = priced_lines(
        db,
        [{"sku": first["sku"], "qty": 1}, {"sku": second["sku"], "qty": 1}],
    )
    by_sku = {line["sku"]: line["price_cents"] for line in priced}
    assert by_sku[first["sku"]] == first["price_cents"]
    assert by_sku[second["sku"]] == second["regular"]


def test_offer_schedule_is_nineteen_and_editable():
    import json

    from shop.staff import save_staff

    client = _client()
    db = client.app.state.db
    free = json.loads(db.execute("select value from promos where key = 'free_shipping_cents'").fetchone()["value"])
    tiers = json.loads(db.execute("select value from promos where key = 'tiers'").fetchone()["value"])
    first = db.execute("select threshold_cents, amount_cents from coupons where kind = 'first'").fetchone()
    assert free == 1900
    assert tiers == [[4000, 300], [5000, 500], [10000, 1000], [20000, 2000]]
    assert (first["threshold_cents"], first["amount_cents"]) == (2500, 200)
    save_staff(db, "admin", "secret-pass", "admin")
    client.post("/admin/login", data={"username": "admin", "password": "secret-pass"}, follow_redirects=False)
    saved = client.post(
        "/admin/promos",
        data={
            "free_shipping_cents": "1900",
            "first_over": "3000",
            "first_off": "300",
            "tier_over": ["4000", "9000", ""],
            "tier_off": ["300", "800", ""],
        },
        follow_redirects=False,
    )
    assert saved.status_code == 303
    first = db.execute("select threshold_cents, amount_cents from coupons where kind = 'first'").fetchone()
    tiers = json.loads(db.execute("select value from promos where key = 'tiers'").fetchone()["value"])
    assert (first["threshold_cents"], first["amount_cents"]) == (3000, 300)
    assert tiers == [[4000, 300], [9000, 800]]


def test_seckill_price_is_what_the_cart_charges():
    from shop.checkout import place_order

    client = _client()
    db = client.app.state.db
    row = db.execute(
        """
        select ci.id, ci.sku, ci.price_cents, ci.stock
        from campaign_items ci
        join campaigns c on c.id = ci.campaign_id
        where c.kind = 'seckill'
        order by ci.id
        limit 1
        """
    ).fetchone()
    priced, _total = priced_lines(db, [{"sku": row["sku"], "qty": 1}])
    assert priced[0]["price_cents"] == row["price_cents"]
    assert priced[0]["campaign_item_id"]
    promos = {
        item["key"]: __import__("json").loads(item["value"])
        for item in db.execute("select key, value from promos").fetchall()
    }
    promos["tiers"] = [tuple(pair) for pair in promos["tiers"]]
    place_order(
        db,
        promos,
        client.app.state.outbox,
        lines=[{"sku": row["sku"], "qty": 1}],
        submit_id="sale-1",
        email="buyer@example.com",
        name="A Buyer",
        address="1 Road",
        city="Austin",
        region="TX",
        postal="73301",
        ship_country="US",
        phone="5551212",
        currency="USD",
        units=100,
        minor_units=2,
        use_balance=False,
        coupon_id=None,
        referrer=None,
    )
    left = db.execute("select stock from campaign_items where id = ?", (row["id"],)).fetchone()["stock"]
    assert left == row["stock"] - 1
