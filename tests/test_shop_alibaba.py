import io
import json
from decimal import Decimal

from fastapi.testclient import TestClient
from openpyxl import Workbook

from shop.alibaba import apply_prices, category_for, detail_image_urls, markup_cents, parse_sheet, sku_price
from shop.app import create_app
from shop.staff import save_staff


SHEET = (
    "导出说明\n"
    "商品ID,商品标题,类目名称,货号,价格,起订量,库存,单位,品牌,材质,颜色,重量,长,宽,高,发货港口,主图,产品属性\n"
    "665544,不锈钢沥水架,厨房用品,HR-9,72,2,50,件,Harbor,不锈钢,银色,0.4kg,30,20,10,宁波,https://img.example/rack.jpg,产地:浙江\n"
)


def test_each_sku_takes_the_higher_of_markup_and_weight():
    light = sku_price(100, "20g", "", Decimal("1.3"), Decimal("1.1"))
    assert light["price_cents"] == 110
    assert light["original_cents"] == 130
    assert light["hold"] is False
    heavy = sku_price(100, "50g", "", Decimal("1"), Decimal("1"))
    assert heavy["price_cents"] == 167
    assert heavy["hold"] is True
    mild = sku_price(1000, "330g", "", Decimal("1"), Decimal("1"))
    assert mild["price_cents"] == 1100
    assert mild["hold"] is False
    blocked = sku_price(1000, "360g", "", Decimal("1"), Decimal("1"))
    assert blocked["price_cents"] == 1200
    assert blocked["hold"] is True


def test_saved_grams_and_percent_change_the_price():
    loose = sku_price(100, "50g", "", Decimal("1"), Decimal("1"), grams_per_dollar=30, hold_percent=70)
    assert loose["price_cents"] == 167
    assert loose["hold"] is False
    tight = sku_price(100, "20g", "", Decimal("1"), Decimal("1"), grams_per_dollar=10, hold_percent=20)
    assert tight["price_cents"] == 200
    assert tight["hold"] is True


def test_upload_files_stationery_separately_from_desk():
    assert category_for("文具", "中性笔 0.5") == "office"
    assert category_for("办公文具套装") == "office"
    assert category_for("", "笔记本") == "office"
    assert category_for("桌面收纳盒") == "office"
    assert category_for("厨房用品", "不锈钢沥水架") == "kitchen"
    assert category_for("宠物食盆") == "pet"
    assert category_for("毛巾浴巾") == "textile"
    assert category_for("") == "daily"


def test_alibaba_sheet_keeps_one_title_and_the_parameters():
    items = parse_sheet(SHEET.encode("utf-8"), "goods.csv")
    ready, errors = apply_prices(items, 7.2)
    assert errors == []
    item = ready[0]
    assert item["sku"] == "hr-9"
    assert item["title"] == "不锈钢沥水架"
    assert "ja" not in item
    assert item["category"] == "kitchen"
    assert item["money"] == "CNY"
    assert item["price_cents"] == 7200
    assert item["stock"] == 50
    listing = item["listing"]
    assert listing["moq"] == "2"
    assert listing["unit"] == "件"
    assert listing["brand"] == "Harbor"
    assert listing["material"] == "不锈钢"
    assert listing["color"] == "银色"
    assert listing["weight"] == "0.4kg"
    assert listing["size"] == "30 × 20 × 10 cm"
    assert listing["port"] == "宁波"
    assert listing["origin"] == "浙江"
    assert listing["images"] == ["https://img.example/rack.jpg"]


def test_rmb_number_is_the_dollar_amount_before_markup():
    raw = "商品标题,价格\n抹布,0.35\n"
    ready, errors = apply_prices(parse_sheet(raw.encode("utf-8"), "a.csv"), None)
    assert errors == []
    assert ready[0]["price_cents"] == 35
    assert markup_cents(35, Decimal("1.1")) == 39
    assert markup_cents(35, Decimal("1.3")) == 46


def test_fob_price_stays_in_dollars_and_a_range_uses_the_low_number():
    raw = "产品名称,FOB价格,币种\nDish rack,1.20-3.40,USD\n"
    ready, errors = apply_prices(parse_sheet(raw.encode("utf-8"), "a.csv"), None)
    assert errors == []
    assert ready[0]["money"] == "USD"
    assert ready[0]["price_cents"] == 120


def test_color_rows_of_one_offer_stay_separate():
    raw = "商品ID,商品标题,价格,颜色\n100,杯子,10,黑色\n100,杯子,10,白色\n"
    items = parse_sheet(raw.encode("utf-8"), "a.csv")
    assert len(items) == 2
    assert items[0]["sku"] != items[1]["sku"]
    assert items[0]["listing"]["color"] == "黑色"
    assert items[1]["listing"]["color"] == "白色"


def test_excel_file_uses_the_same_columns():
    book = Workbook()
    sheet = book.active
    sheet.append(["说明"])
    sheet.append(["商品标题", "价格", "货号"])
    sheet.append(["喷油壶", 8, "OS-1"])
    buffer = io.BytesIO()
    book.save(buffer)
    items = parse_sheet(buffer.getvalue(), "goods.xlsx")
    assert items[0]["sku"] == "os-1"
    assert items[0]["title"] == "喷油壶"
    assert items[0]["money"] == "CNY"
    assert items[0]["amount"] == 8


def test_gb18030_csv_is_read():
    raw = "商品标题,FOB价格\n硅胶铲,6\n".encode("gb18030")
    items = parse_sheet(raw, "goods.csv")
    assert items[0]["title"] == "硅胶铲"
    assert items[0]["money"] == "USD"
    assert items[0]["amount"] == 6


def _login(client):
    save_staff(client.app.state.db, "admin", "secret", "admin")
    client.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)


def _finish(client):
    import time

    job = {}
    for _ in range(400):
        job = client.get("/admin/catalog/progress").json()
        if not job["running"]:
            return job
        time.sleep(0.01)
    raise AssertionError(job)


def _publish(client):
    response = client.post("/admin/catalog/publish", follow_redirects=False)
    assert response.status_code == 303
    job = _finish(client)
    assert job["error"] == ""
    return job


def _client(**kwargs):
    kwargs.setdefault("image_fetch", lambda url, sku, index: "")
    return TestClient(create_app(units_per_usd=150, db_path=":memory:", **kwargs))


def test_one_product_and_a_selection_can_be_deleted():
    client = _client()
    _login(client)
    page = client.get("/admin/products")
    assert "删除选中" in page.text
    assert 'name="sku"' in page.text
    one = client.post("/admin/products/drain-rack/delete", follow_redirects=False)
    assert one.status_code == 303
    assert client.app.state.db.execute("select sku from products where sku = 'drain-rack'").fetchone() is None
    many = client.post(
        "/admin/catalog/delete",
        data={"sku": ["binder-clip", "oil-sprayer"]},
        follow_redirects=False,
    )
    assert many.status_code == 303
    left = {
        row["sku"]
        for row in client.app.state.db.execute("select sku from products").fetchall()
    }
    assert "binder-clip" not in left
    assert "oil-sprayer" not in left
    assert "note-holder" in left


def test_admin_key_uses_grok_and_is_not_shown_again(monkeypatch):
    calls = []

    def fake_pair(key, base, model):
        calls.append((key, base, model))

        def writer(facts):
            return {"title": "Dish cloth", "description": "Wipes the counter."}

        def translate(text, source, target):
            return text

        return writer, translate

    monkeypatch.setattr("shop.app.ai_pair", fake_pair)
    client = _client()
    _login(client)
    page = client.get("/admin/products")
    assert 'name="ai_model" value="auto"' in page.text
    assert 'name="ai_base" value="https://api.cursor.com"' in page.text
    saved = client.post(
        "/admin/ai",
        data={"ai_key": "cursor-secret-key-1234", "ai_model": "grok-4.7", "ai_base": "https://api.x.ai/v1"},
        follow_redirects=True,
    )
    assert "cursor-secret-key-1234" not in saved.text
    assert "1234" in saved.text
    response = client.post(
        "/admin/catalog/file",
        data={"list_rate": "1", "sale_rate": "1"},
        files={"file": ("goods.csv", "商品标题,FOB价格,货号\n抹布,1,CLOTH\n".encode(), "text/csv")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    _finish(client)
    _publish(client)
    assert "Dish cloth" in client.get("/?country=US").text
    assert calls[0] == ("cursor-secret-key-1234", "https://api.x.ai/v1", "grok-4.7")


def test_product_admin_has_one_title_column(monkeypatch):
    monkeypatch.delenv("DEEPL_AUTH_KEY", raising=False)
    client = _client()
    _login(client)
    page = client.get("/admin/products")
    assert page.status_code == 200
    assert "<th>日文</th>" not in page.text
    assert "<th>英文</th>" not in page.text
    assert "改文案" not in page.text
    assert "Oil sprayer" in page.text
    assert "オイルスプレー" not in page.text
    assert "上传阿里巴巴商品表" in page.text
    assert "<th>起订量</th>" not in page.text
    assert "原价倍率" in page.text
    assert "售价倍率" in page.text
    assert "拦截百分比" in page.text
    assert 'name="grams_per_dollar" value="30"' in page.text
    assert 'name="hold_percent" value="20"' in page.text


def test_admin_saves_pricing_rules_and_upload_uses_them(monkeypatch):
    monkeypatch.delenv("DEEPL_AUTH_KEY", raising=False)
    client = _client()
    _login(client)
    bad = client.post(
        "/admin/pricing",
        data={"list_rate": "1.3", "sale_rate": "0", "hold_percent": "20", "grams_per_dollar": "30"},
        follow_redirects=False,
    )
    assert bad.status_code == 400
    saved = client.post(
        "/admin/pricing",
        data={"list_rate": "1.3", "sale_rate": "1.1", "hold_percent": "300", "grams_per_dollar": "15"},
        follow_redirects=False,
    )
    assert saved.status_code == 303
    page = client.get("/admin/products")
    assert 'name="grams_per_dollar" value="15"' in page.text
    assert 'name="hold_percent" value="300"' in page.text
    raw = "商品标题,价格,货号,重量,类目名称\n轻夹,1,LT-1,50g,厨房\n"
    response = client.post(
        "/admin/catalog/file",
        data={"list_rate": "1", "sale_rate": "1"},
        files={"file": ("goods.csv", raw.encode("utf-8"), "text/csv")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    _finish(client)
    row = client.app.state.db.execute("select price_cents, listing from products where sku = 'lt-1'").fetchone()
    assert row["price_cents"] == 333
    assert "拦截" not in row["listing"]


def test_upload_keeps_chinese_off_the_store_until_translation(monkeypatch):
    monkeypatch.delenv("DEEPL_AUTH_KEY", raising=False)
    client = _client()
    _login(client)
    client.app.state.db.execute(
        "insert into rates (currency, hour, units_per_usd) values ('CNY', '2026-11-02T06', 7.2)"
    )
    missing = client.post(
        "/admin/catalog/file",
        data={"list_rate": "", "sale_rate": ""},
        files={"file": ("goods.csv", SHEET.encode("utf-8"), "text/csv")},
        follow_redirects=False,
    )
    assert missing.status_code == 400
    assert client.app.state.db.execute("select sku from products where sku = 'hr-9'").fetchone() is None
    response = client.post(
        "/admin/catalog/file",
        data={"list_rate": "1", "sale_rate": "1"},
        files={"file": ("goods.csv", SHEET.encode("utf-8"), "text/csv")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    _finish(client)
    row = client.app.state.db.execute("select price_cents, published, names from products where sku = 'hr-9'").fetchone()
    assert row["price_cents"] == 7200
    assert row["published"] == 0
    assert "沥" not in row["names"]
    home = client.get("/?country=US")
    assert "不锈钢沥水架" not in home.text
    assert client.get("/p/hr-9?country=US").status_code == 404
    admin = client.get("/admin/products")
    assert "不锈钢沥水架" in admin.text
    assert "<th>日文</th>" not in admin.text
    assert "待翻译" in admin.text
    assert "品牌" in admin.text
    assert "Harbor" in admin.text


def test_upload_translates_the_one_title_from_english():
    seen = []

    def translate(text, source, target):
        seen.append((source, target, text))
        return text

    client = _client(translator=translate)
    _login(client)
    raw = "商品标题,FOB价格,类目名称,货号,材质\n不锈钢沥水架,12.50,厨房,HR-9,不锈钢沥水架\n"
    response = client.post(
        "/admin/catalog/file",
        data={"list_rate": "1", "sale_rate": "1"},
        files={"file": ("goods.csv", raw.encode("utf-8"), "text/csv")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    _finish(client)
    _publish(client)
    home = client.get("/?country=US")
    assert "stainless steel dish rack" in home.text
    assert "沥" not in home.text
    japan = client.get("/p/hr-9?country=JP")
    assert "stainless steel dish rack" in japan.text
    assert "沥" not in japan.text
    assert {row[0] for row in seen if row[1] != "en"} == {"en"}
    admin = client.get("/admin/products")
    assert "不锈钢沥水架" in admin.text
    assert "<th>日文</th>" not in admin.text


def test_markup_sets_original_and_sale_and_each_spec_is_on_the_page():
    def translate(text, source, target):
        if source == "zh" and "黑" in text:
            return "Black"
        if source == "zh" and "白" in text:
            return "White"
        return text

    client = _client(translator=translate)
    _login(client)
    raw = (
        "商品ID,商品标题,FOB价格,规格,货号\n"
        "9,不锈钢沥水架,10,黑色,HR-9\n"
        "9,不锈钢沥水架,12,白色,HR-9\n"
    )
    response = client.post(
        "/admin/catalog/file",
        data={"list_rate": "1.3", "sale_rate": "1.1"},
        files={"file": ("goods.csv", raw.encode("utf-8"), "text/csv")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    _finish(client)
    row = client.app.state.db.execute(
        "select price_cents, original_cents, offers from products where sku = 'hr-9'"
    ).fetchone()
    offers = json.loads(row["offers"])
    assert len(offers) == 2
    assert [offer["price_cents"] for offer in offers] == [1100, 1320]
    assert [offer["original_cents"] for offer in offers] == [1300, 1560]
    assert row["price_cents"] == 1100
    assert row["original_cents"] == 1300
    _publish(client)
    page = client.get("/p/hr-9?country=US")
    assert page.text.count('name="offer"') == 2
    assert "Black" in page.text
    assert "White" in page.text
    assert "$11.00" in page.text
    assert "$13.20" in page.text
    assert "$13.00" in page.text
    assert "Original" in page.text
    assert 'name="color"' not in page.text
    assert "黑" not in page.text
    chosen = offers[1]["id"]
    added = client.post(
        "/cart/add",
        data={"sku": "hr-9", "offer": chosen, "qty": "1", "country": "US"},
        follow_redirects=False,
    )
    assert f"hr-9~{chosen}:1" in added.cookies["cart"]
    cart = client.get("/cart?country=US")
    assert "$13.20" in cart.text
    assert "White" in cart.text


def test_detail_address_column_becomes_pictures():
    raw = "商品标题,FOB价格,货号,详情地址\n抹布,1,CLOTH,https://img.example/d1.jpg https://img.example/d2.jpg\n"
    items = parse_sheet(raw.encode("utf-8"), "goods.csv")
    assert items[0]["listing"]["detail_images"] == [
        "https://img.example/d1.jpg",
        "https://img.example/d2.jpg",
    ]


def test_detail_html_is_a_list_of_pictures():
    html = '<p>尺寸</p><img src="https://img.example/a.jpg"><img data-src="//img.example/b.jpg">'
    assert detail_image_urls(html) == ["https://img.example/a.jpg", "https://img.example/b.jpg"]


def test_detail_pictures_are_downloaded_and_shown():
    import csv

    def fetch(url, sku, index):
        return f"/static/catalog/{sku}/{index}.jpg"

    def translate(text, source, target):
        return "Note stand" if source == "zh" else text

    buffer = io.StringIO()
    csv.writer(buffer).writerows([
        ["商品标题", "FOB价格", "货号", "详情"],
        ["便签座", "4", "NOTE", '<img src="https://img.example/a.jpg"><img src="https://img.example/b.jpg">'],
    ])
    client = _client(image_fetch=fetch, translator=translate)
    _login(client)
    response = client.post(
        "/admin/catalog/file",
        data={"list_rate": "1", "sale_rate": "1"},
        files={"file": ("goods.csv", buffer.getvalue().encode("utf-8"), "text/csv")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    _finish(client)
    row = client.app.state.db.execute("select listing from products where sku = 'note'").fetchone()
    listing = json.loads(row["listing"])
    assert listing["detail_images"] == ["/static/catalog/note/d0.jpg", "/static/catalog/note/d1.jpg"]
    edit = client.get("/admin/products/note")
    assert 'src="/static/catalog/note/d0.jpg"' in edit.text
    assert 'src="/static/catalog/note/d1.jpg"' in edit.text
    assert 'name="description"' not in edit.text
    _publish(client)
    page = client.get("/p/note?country=US")
    assert 'src="/static/catalog/note/d0.jpg"' in page.text
    assert "img.example" not in page.text
    assert "尺寸" not in page.text


def test_alibaba_image_is_copied_onto_our_server():
    seen = []

    def fetch(url, sku, index):
        seen.append((url, sku, index))
        return f"/static/catalog/{sku}/{index}.jpg"

    def translate(text, source, target):
        return "Cup" if source == "zh" else text

    client = _client(image_fetch=fetch, translator=translate)
    _login(client)
    response = client.post(
        "/admin/catalog/file",
        data={"list_rate": "1", "sale_rate": "1"},
        files={"file": ("goods.csv", "商品标题,FOB价格,货号,主图\n杯子,4,CUP,https://img.example/cup.jpg\n".encode(), "text/csv")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    _finish(client)
    assert seen == [("https://img.example/cup.jpg", "cup", 0)]
    row = client.app.state.db.execute("select image_url, offers from products where sku = 'cup'").fetchone()
    assert row["image_url"] == "/static/catalog/cup/0.jpg"
    assert "img.example" not in row["offers"]
    _publish(client)
    home = client.get("/?country=US")
    assert "img.example" not in home.text
    assert "/static/catalog/cup/0.jpg" in home.text


def test_upload_result_stays_on_the_product_page_after_refresh():
    client = _client(translator=lambda text, source, target: text)
    _login(client)
    response = client.post(
        "/admin/catalog/file",
        data={"list_rate": "1", "sale_rate": "1"},
        files={"file": ("goods.csv", "商品标题,FOB价格,货号\n杯子,4,CUP\n".encode(), "text/csv")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    job = _finish(client)
    assert job["running"] is False
    assert job["result"]["imported"] == 1
    assert job["url"].startswith("/admin/products")
    again = client.get("/admin/catalog/progress").json()
    assert again["result"]["imported"] == 1
    page = client.get("/admin/products")
    assert "已导入 1 条" in page.text
    assert "翻译标题和规格并上架" in page.text
    assert page.text.find("翻译标题和规格并上架") < page.text.find("上传阿里巴巴商品表")
    assert 'id="job-card"' in client.get("/admin/orders").text
    stored = json.loads(
        client.app.state.db.execute("select value from settings where key = 'catalog_job'").fetchone()["value"]
    )
    assert stored["result"]["imported"] == 1


def test_translation_runs_several_products_at_once():
    import threading
    import time

    active = {"n": 0, "peak": 0}
    lock = threading.Lock()

    def translate(text, source, target):
        with lock:
            active["n"] += 1
            active["peak"] = max(active["peak"], active["n"])
        time.sleep(0.05)
        with lock:
            active["n"] -= 1
        return "Item" if source == "zh" else text

    client = _client(translator=translate)
    _login(client)
    raw = "商品标题,FOB价格,货号\n甲,1,AA\n乙,1,BB\n"
    response = client.post(
        "/admin/catalog/file",
        data={"list_rate": "1", "sale_rate": "1"},
        files={"file": ("goods.csv", raw.encode("utf-8"), "text/csv")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    _finish(client)
    _publish(client)
    assert active["peak"] >= 2
    page = client.get("/admin/products")
    assert "已翻译上架 2 条" in page.text


def test_restart_keeps_an_interrupted_job_on_the_product_page(tmp_path):
    path = str(tmp_path / "shop.sqlite")
    first = create_app(units_per_usd=150, db_path=path, translator=lambda text, source, target: text)
    first.state.db.execute(
        "insert into settings (key, value) values ('catalog_job', ?) on conflict(key) do update set value = excluded.value",
        (
            json.dumps(
                {
                    "running": True,
                    "kind": "upload",
                    "phase": "保存商品",
                    "done": 2,
                    "total": 5,
                    "label": "杯子",
                    "error": "",
                    "url": "",
                    "workers": 0,
                    "result": {"imported": 2, "held": 2, "skipped": 0, "published": 0, "failed": 0},
                },
                ensure_ascii=False,
            ),
        ),
    )
    second = create_app(units_per_usd=150, db_path=path, translator=lambda text, source, target: text)
    save_staff(second.state.db, "admin", "secret", "admin")
    client = TestClient(second)
    client.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)
    page = client.get("/admin/products")
    assert "上次处理中断了" in page.text
    assert "已导入 2 条" in page.text
    assert client.get("/admin/catalog/progress").json()["running"] is False


def test_unreachable_translator_is_not_shown_as_published():
    def translate(text, source, target):
        raise ConnectionError("10061")

    client = _client(translator=translate)
    _login(client)
    raw = "商品标题,FOB价格,货号\n甲,1,AA\n乙,1,BB\n"
    response = client.post(
        "/admin/catalog/file",
        data={"list_rate": "1", "sale_rate": "1"},
        files={"file": ("goods.csv", raw.encode("utf-8"), "text/csv")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    _finish(client)
    started = client.post("/admin/catalog/publish", follow_redirects=False)
    assert started.status_code == 303
    job = _finish(client)
    assert "连不上翻译接口" in job["error"]
    page = client.get("/admin/products?section=import")
    assert "连不上翻译接口" in page.text
    assert "没有上架" in page.text
    assert "已翻译上架" not in page.text
    assert client.app.state.db.execute("select count(*) as n from products where published = 0").fetchone()["n"] == 2


def test_connection_errors_do_not_drop_the_rest_of_the_batch():
    def translate(text, source, target):
        raise ConnectionError("10061")

    client = _client(translator=translate)
    _login(client)
    lines = ["商品标题,FOB价格,货号"]
    lines.extend(f"货{i},1,S{i:02d}" for i in range(19))
    response = client.post(
        "/admin/catalog/file",
        data={"list_rate": "1", "sale_rate": "1"},
        files={"file": ("goods.csv", "\n".join(lines).encode("utf-8"), "text/csv")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    _finish(client)
    started = client.post("/admin/catalog/publish", follow_redirects=False)
    assert started.status_code == 303
    job = _finish(client)
    assert job["done"] == 19
    assert job["result"]["published"] == 0
    assert job["result"]["failed"] == 19
    assert "连不上翻译接口" in job["error"]


def test_one_slow_title_does_not_stop_the_rest():
    def translate(text, source, target):
        if source == "zh" and "甲" in text:
            raise TimeoutError("timed out")
        return "Item" if source == "zh" else text

    client = _client(translator=translate)
    _login(client)
    raw = "商品标题,FOB价格,货号\n甲,1,AA\n乙,1,BB\n"
    response = client.post(
        "/admin/catalog/file",
        data={"list_rate": "1", "sale_rate": "1"},
        files={"file": ("goods.csv", raw.encode("utf-8"), "text/csv")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    _finish(client)
    started = client.post("/admin/catalog/publish", follow_redirects=False)
    assert started.status_code == 303
    job = _finish(client)
    assert job["done"] == 2
    assert job["result"]["published"] == 1
    assert job["result"]["failed"] == 1
    assert "连不上" not in job["error"]
    page = client.get("/admin/products?section=import")
    assert "已翻译上架 1 条" in page.text
    assert "1 条没译成" in page.text
