import json

from fastapi.testclient import TestClient

from shop.app import create_app
from shop.staff import save_staff
from shop.writer import write_english, write_listing


def _client(**kwargs):
    kwargs.setdefault("image_fetch", lambda url, sku, index: "")
    client = TestClient(create_app(units_per_usd=150, db_path=":memory:", **kwargs))
    save_staff(client.app.state.db, "admin", "secret", "admin")
    client.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)
    return client


def test_one_product_can_be_edited_with_its_details():
    client = _client()
    page = client.get("/admin/products/drain-rack")
    assert page.status_code == 200
    assert "详情" in page.text
    assert 'src="/static/products/drain-rack.svg"' in page.text
    assert 'name="description"' not in page.text
    assert "供应商链接" in page.text
    assert "Dish rack" in page.text
    saved = client.post(
        "/admin/products/drain-rack/save",
        data={
            "title": "沥水架",
            "description": "放在水槽边，用来竖放盘子。",
            "category": "kitchen",
            "stock": "80",
            "price": "15.00",
            "original": "18.00",
            "material": "不锈钢",
            "size": "30cm",
            "weight": "1kg",
            "cargo": "DR-1",
            "offer_id": "665544",
            "url": "https://detail.1688.com/offer/665544.html",
        },
        follow_redirects=False,
    )
    assert saved.status_code == 303
    row = client.app.state.db.execute("select * from products where sku = 'drain-rack'").fetchone()
    assert row["price_cents"] == 1500
    assert row["original_cents"] == 1800
    assert row["stock"] == 80
    listing = json.loads(row["listing"])
    assert listing["description"] == "放在水槽边，用来竖放盘子。"
    assert listing["offer_id"] == "665544"
    assert listing["url"].endswith("/665544.html")
    home = client.get("/?country=US")
    assert "放在水槽边" not in home.text


def test_paid_orders_become_one_supplier_list():
    client = _client()
    client.post(
        "/admin/products/drain-rack/save",
        data={
            "title": "沥水架",
            "description": "水槽边用",
            "category": "kitchen",
            "stock": "100",
            "price": "12.00",
            "original": "12.00",
            "offer_id": "665544",
            "cargo": "DR-1",
            "url": "",
        },
        follow_redirects=False,
    )
    db = client.app.state.db
    for submit_id, qty in (("buy-1", 2), ("buy-2", 1)):
        inserted = db.execute(
            """
            insert into orders (submit_id, email, status, currency, units_per_usd, due_cents, due_local)
            values (?, 'buyer@example.com', 'paid', 'USD', 1, 1200, 1200)
            """,
            (submit_id,),
        )
        db.execute(
            "insert into order_lines (order_id, sku, price_cents, qty) values (?, 'drain-rack', 1200, ?)",
            (inserted.lastrowid, qty),
        )
    page = client.get("/admin/purchasing")
    assert page.status_code == 200
    assert "沥水架" in page.text
    assert "https://detail.1688.com/offer/665544.html" in page.text
    assert ">3<" in page.text
    done = client.post("/admin/purchasing/bought", data={"sku": "drain-rack"}, follow_redirects=False)
    assert done.status_code == 303
    again = client.get("/admin/purchasing")
    assert "没有待采购的商品" in again.text


def test_order_shows_the_chinese_sku_after_the_title_is_english():
    client = _client()
    db = client.app.state.db
    offers = [{
        "id": "ZH-STZJ-001",
        "code": "ZH-STZJ-001",
        "source_label": "玛瑙绿",
        "label": {"en": "Agate Green"},
        "source_cents": 35,
        "price_cents": 39,
        "original_cents": 46,
    }]
    listing = {"title": "牛皮护掌健身手套", "cargo": "ZL-1"}
    db.execute(
        "update products set offers = ?, listing = ?, names = ? where sku = 'drain-rack'",
        (
            json.dumps(offers, ensure_ascii=False),
            json.dumps(listing, ensure_ascii=False),
            json.dumps({"en": "Cowhide Palm-Guard Fitness Gloves"}, ensure_ascii=False),
        ),
    )
    inserted = db.execute(
        """
        insert into orders (submit_id, email, status, currency, units_per_usd, due_cents, due_local)
        values ('buy-color', 'buyer@example.com', 'paid', 'USD', 1, 39, 39)
        """
    )
    db.execute(
        "insert into order_lines (order_id, sku, price_cents, qty) values (?, 'drain-rack~ZH-STZJ-001', 39, 2)",
        (inserted.lastrowid,),
    )
    page = client.get(f"/admin/orders/{inserted.lastrowid}")
    assert page.status_code == 200
    assert "ZH-STZJ-001" in page.text
    assert "玛瑙绿" in page.text
    assert "牛皮护掌健身手套" in page.text
    assert "Cowhide Palm-Guard Fitness Gloves" in page.text
    buying = client.get("/admin/purchasing")
    assert "ZH-STZJ-001" in buying.text
    assert "玛瑙绿" in buying.text
    assert "牛皮护掌健身手套" in buying.text
    catalog = client.get("/admin/products")
    assert "ZH-STZJ-001" in catalog.text
    assert "玛瑙绿" in catalog.text


def test_several_skus_stay_out_of_the_cart_until_one_is_chosen():
    client = _client()
    offers = [
        {"id": "A-1", "label": {"en": "Green", "ja": "グリーン"}, "price_cents": 100, "original_cents": 100},
        {"id": "A-2", "label": {"en": "Black", "ja": "ブラック"}, "price_cents": 120, "original_cents": 120},
    ]
    client.app.state.db.execute(
        "update products set offers = ? where sku = 'drain-rack'",
        (json.dumps(offers, ensure_ascii=False),),
    )
    skipped = client.post(
        "/cart/add",
        data={"sku": "drain-rack", "qty": "1", "country": "JP"},
        follow_redirects=False,
    )
    assert skipped.status_code == 303
    assert "/p/drain-rack" in skipped.headers["location"]
    assert "cart" not in skipped.cookies
    page = client.get("/p/drain-rack?country=JP")
    assert "グリーン" in page.text
    assert "ブラック" in page.text
    assert page.text.count('name="offer"') == 2
    assert "checked" not in page.text
    added = client.post(
        "/cart/add",
        data={"sku": "drain-rack", "offer": "A-2", "qty": "1", "country": "JP"},
        follow_redirects=False,
    )
    assert "drain-rack~A-2:1" in added.cookies["cart"]
    japan = client.get("/checkout?country=JP")
    assert "追加" not in japan.text
    assert "入れる" in japan.text or "選ぶ" in japan.text


def test_ai_writes_the_selling_title_before_other_languages():
    seen = []

    def writer(facts):
        assert "沥" in facts["title"]
        return {"title": "Compact dish rack", "description": "Stands beside the sink."}

    def translate(text, source, target):
        seen.append((source, target, text))
        return text

    client = _client(translator=translate, writer=writer)
    raw = "商品标题,FOB价格,货号,详情\n不锈钢沥水架,10,HR-9,放在水槽边\n"
    response = client.post(
        "/admin/catalog/file",
        data={"list_rate": "1", "sale_rate": "1.1"},
        files={"file": ("goods.csv", raw.encode("utf-8"), "text/csv")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    from tests.test_shop_alibaba import _finish, _publish
    _finish(client)
    _publish(client)
    home = client.get("/?country=US")
    assert "Compact dish rack" in home.text
    assert "沥" not in home.text
    product = client.get("/p/hr-9?country=US")
    assert "Stands beside the sink." in product.text
    assert {row[0] for row in seen if row[1] != "en"} == {"en"}
    japan = client.get("/p/hr-9?country=JP")
    assert "Compact dish rack" in japan.text


def test_writer_reads_json_surrounded_by_prose():
    def complete(prompt):
        return 'Here is the listing:\n{"title": "Dish rack", "description": "Holds plates."}\nThanks'

    written = write_english({"title": "沥水架", "options": []}, complete)
    assert written["title"] == "Dish rack"


def test_one_listing_call_covers_every_language():
    calls = []

    def complete(prompt):
        calls.append(prompt)
        return json.dumps({
            "title": {
                "en": "Door stop",
                "es": "Tope",
                "de": "Turstopper",
                "fr": "Butoir",
                "pt": "Calco",
                "ja": "ドアストッパー",
            },
            "description": {
                "en": "Soft silicone.",
                "es": "Silicona.",
                "de": "Silikon.",
                "fr": "Silicone.",
                "pt": "Silicone.",
                "ja": "シリコン。",
            },
            "material": {"en": "Silicone", "ja": "シリコン"},
            "options": [{
                "en": "White",
                "es": "Blanco",
                "de": "Weiss",
                "fr": "Blanc",
                "pt": "Branco",
                "ja": "白",
            }],
        })

    written = write_listing(
        {"title": "门挡", "description": "硅胶", "material": "硅胶", "options": ["白色"]},
        complete,
    )
    assert len(calls) == 1
    assert written["localized"] is True
    assert written["title"]["ja"] == "ドアストッパー"
    assert written["options"][0]["ja"] == "白"


def test_missing_languages_take_one_more_call():
    calls = {"n": 0}

    def complete(prompt):
        calls["n"] += 1
        if calls["n"] == 1:
            return json.dumps({"title": {"en": "Door stop"}, "description": {"en": "Soft."}, "options": []})
        return json.dumps({
            "title": {"ja": "ドアストッパー", "es": "Tope", "de": "Turstopper", "fr": "Butoir", "pt": "Calco"},
            "description": {"ja": "シリコン。", "es": "Silicona.", "de": "Silikon.", "fr": "Silicone.", "pt": "Silicone."},
        })

    written = write_listing({"title": "门挡", "options": []}, complete)
    assert calls["n"] == 2
    assert written["title"]["en"] == "Door stop"
    assert written["title"]["ja"] == "ドアストッパー"


def test_published_listing_does_not_open_a_robot_per_language():
    seen = []

    def writer(facts):
        assert "门挡" in facts["title"]
        return {
            "localized": True,
            "title": {
                "en": "Door stop",
                "es": "Tope",
                "de": "Turstopper",
                "fr": "Butoir",
                "pt": "Calco",
                "ja": "ドアストッパー",
            },
            "description": {
                "en": "Soft silicone.",
                "es": "Silicona.",
                "de": "Silikon.",
                "fr": "Silicone.",
                "pt": "Silicone.",
                "ja": "シリコン。",
            },
            "options": [{
                "en": "White",
                "es": "Blanco",
                "de": "Weiss",
                "fr": "Blanc",
                "pt": "Branco",
                "ja": "白",
            }],
        }

    def translate(text, source, target):
        seen.append((source, target, text))
        return text

    client = _client(translator=translate, writer=writer)
    raw = "商品标题,FOB价格,货号,颜色,详情\n门挡,2,DOOR-1,白色,硅胶\n"
    response = client.post(
        "/admin/catalog/file",
        data={"list_rate": "1", "sale_rate": "1"},
        files={"file": ("goods.csv", raw.encode("utf-8"), "text/csv")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    from tests.test_shop_alibaba import _finish, _publish

    _finish(client)
    _publish(client)
    assert seen == []
    japan = client.get("/p/door-1?country=JP")
    assert "ドアストッパー" in japan.text
    assert "シリコン。" in japan.text
    offers = json.loads(client.app.state.db.execute("select offers from products where sku = 'door-1'").fetchone()["offers"])
    assert offers[0]["label"]["ja"] == "白"


def test_writer_rejects_a_chinese_title():
    def complete(prompt):
        return '{"title": "沥水架", "description": "ok"}'

    try:
        write_english({"title": "沥水架"}, complete)
    except ValueError:
        return
    raise AssertionError("chinese title")
