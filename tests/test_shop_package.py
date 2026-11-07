import io
import json
import shutil
import zipfile
from pathlib import Path

from openpyxl import Workbook

from shop.app import ROOT
from tests.test_shop_alibaba import _client, _finish, _login

JPEG = b"\xff\xd8\xff\xd9"


def _package():
    book = Workbook()
    sheet = book.active
    sheet.append(["供应商名称", "资料编码", "商品名称", "颜色", "规格", "商品编码", "供货价", "零售价", "分销控价", "库存", "重量"])
    sheet.append(["昀晗", "pack-1", "迷你挂历", "随机图案-1本", "无规格", "SKU-1", 1.05, 1.69, "", 10, 0.012])
    sheet.append(["昀晗", "pack-1", "迷你挂历", "随机图案-2本", "无规格", "SKU-2", 2.10, 2.30, "", 5, 0.024])
    sheet_buffer = io.BytesIO()
    book.save(sheet_buffer)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("数据包/商品数据-pack-1.xlsx", sheet_buffer.getvalue())
        bundle.writestr("数据包/商品主图/商品主图_1.jpg", JPEG)
        bundle.writestr("数据包/商品详情页图/商品详情页图_1.jpg", JPEG)
        bundle.writestr("数据包/商品详情页图/商品详情页图_2.jpg", JPEG + b"\x00")
        bundle.writestr("数据包/颜色图/颜色图_1.jpg", JPEG)
        bundle.writestr("数据包/颜色图/颜色图_2.jpg", JPEG)
    return archive.getvalue()


def test_jushuitan_zip_copies_detail_pictures(monkeypatch):
    monkeypatch.delenv("DEEPL_AUTH_KEY", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    folder = Path(ROOT) / "static" / "catalog" / "pack-1"
    shutil.rmtree(folder, ignore_errors=True)

    def translate(text, source, target):
        return "Mini calendar" if source == "zh" else text

    client = _client(translator=translate)
    _login(client)
    client.app.state.db.execute(
        "insert into rates (currency, hour, units_per_usd) values ('CNY', '2026-11-02T08', 7.2)"
    )
    try:
        response = client.post(
            "/admin/catalog/file",
            data={"list_rate": "1", "sale_rate": "1"},
            files={"file": ("goods.zip", _package(), "application/zip")},
            follow_redirects=False,
        )
        assert response.status_code == 303
        job = _finish(client)
        assert job["error"] == ""
        assert job["phase"] == "保存商品"
        assert job["done"] == 1
        assert job["total"] == 1
        row = client.app.state.db.execute("select * from products where sku = 'pack-1'").fetchone()
        assert row["published"] == 0
        assert row is not None
        listing = json.loads(row["listing"])
        assert listing["detail_images"] == [
            "/static/catalog/pack-1/d0.jpg",
            "/static/catalog/pack-1/d1.jpg",
        ]
        assert listing["money"] == "USD"
        assert listing["amount"] == 1.05
        offers = json.loads(row["offers"])
        assert [offer["code"] for offer in offers] == ["SKU-1", "SKU-2"]
        assert [offer["id"] for offer in offers] == ["SKU-1", "SKU-2"]
        assert [offer["source_label"] for offer in offers] == ["随机图案-1本", "随机图案-2本"]
        assert [offer["source_cents"] for offer in offers] == [105, 210]
        assert row["price_cents"] == 105
        edit = client.get("/admin/products/pack-1")
        assert 'src="/static/catalog/pack-1/d0.jpg"' in edit.text
        assert 'src="/static/catalog/pack-1/d1.jpg"' in edit.text
        assert "$1.05" in edit.text
        published = client.post("/admin/catalog/publish", follow_redirects=False)
        assert published.status_code == 303
        assert _finish(client)["phase"] == "翻译"
        page = client.get("/p/pack-1?country=US")
        assert page.status_code == 200
        assert 'src="/static/catalog/pack-1/d0.jpg"' in page.text
        assert "迷你" not in page.text
        assert "$1.05" in page.text
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def test_each_product_folder_keeps_its_own_sku_and_pictures():
    def sheet(code, sku, title):
        book = Workbook()
        page = book.active
        page.append(["资料编码", "商品名称", "颜色", "规格", "商品编码", "供货价", "库存", "重量"])
        page.append([code, title, "红色", "无规格", sku, 1.05, 3, 0.1])
        buffer = io.BytesIO()
        book.save(buffer)
        return buffer.getvalue()

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("包-A/商品数据-a.xlsx", sheet("code-a", "AAA-1", "甲"))
        bundle.writestr("包-A/商品详情页图/商品详情页图_1.jpg", JPEG)
        bundle.writestr("包-B/商品数据-b.xlsx", sheet("起苗器", "BBB-2", "乙"))
        bundle.writestr("包-B/商品详情页图/商品详情页图_1.jpg", JPEG + b"\x01")
    from shop.package import read_package

    items = {item["sku"]: item for item in read_package(archive.getvalue(), 1, 1)}
    assert set(items) == {"code-a", "bbb-2"}
    assert items["code-a"]["details"] == [JPEG]
    assert items["bbb-2"]["details"] == [JPEG + b"\x01"]
    assert items["code-a"]["offers"][0]["id"] == "AAA-1"
    assert items["bbb-2"]["offers"][0]["code"] == "BBB-2"


def test_only_the_heavy_spec_is_held():
    from decimal import Decimal

    from shop.package import preview_sheets

    book = Workbook()
    sheet = book.active
    sheet.append(["供应商名称", "资料编码", "商品名称", "颜色", "规格", "商品编码", "供货价", "零售价", "分销控价", "库存", "重量"])
    sheet.append(["昀晗", "box-1", "首饰盒", "7cm 1个装", "无规格", "A", 0.74, 1, "", 10, 0.02])
    sheet.append(["昀晗", "box-1", "首饰盒", "9cm 5个装", "无规格", "B", 1.83, 2, "", 10, 0.096])
    buffer = io.BytesIO()
    book.save(buffer)
    products = preview_sheets(
        [(buffer.getvalue(), "商品数据.xlsx")],
        Decimal("1.3"), Decimal("1.2"), Decimal("30"), Decimal("20"),
    )
    assert len(products) == 1
    assert products[0]["listing"]["hold"] == ""
    assert products[0]["price_cents"] == 89
    assert [offer["hold"] for offer in products[0]["offers"]] == [False, True]


def test_jushuitan_sheet_alone_asks_for_the_zip(monkeypatch):
    monkeypatch.delenv("DEEPL_AUTH_KEY", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    book = Workbook()
    sheet = book.active
    sheet.append(["资料编码", "商品名称", "供货价"])
    sheet.append(["pack-1", "迷你挂历", 1.05])
    buffer = io.BytesIO()
    book.save(buffer)
    client = _client()
    _login(client)
    page = client.post(
        "/admin/catalog/file",
        data={"list_rate": "1", "sale_rate": "1"},
        files={"file": ("商品数据.xlsx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert page.status_code == 400
    assert "商品数据包" in page.text


def _sheet(code, title, price, weight, sku_code):
    book = Workbook()
    sheet = book.active
    sheet.append(["供应商名称", "资料编码", "商品名称", "颜色", "规格", "商品编码", "供货价", "零售价", "分销控价", "库存", "重量"])
    sheet.append(["昀晗", code, title, "默认", "无规格", sku_code, price, price, "", 10, weight])
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def test_preview_reads_the_sheet_and_commit_skips_held_images(monkeypatch):
    monkeypatch.delenv("DEEPL_AUTH_KEY", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    light = Path(ROOT) / "static" / "catalog" / "light-1"
    heavy = Path(ROOT) / "static" / "catalog" / "heavy-1"
    shutil.rmtree(light, ignore_errors=True)
    shutil.rmtree(heavy, ignore_errors=True)
    light_sheet = _sheet("light-1", "轻夹", 1.05, 0.012, "SKU-L")
    heavy_sheet = _sheet("heavy-1", "重夹", 1, 0.05, "SKU-H")
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("轻/商品数据.xlsx", light_sheet)
        bundle.writestr("轻/商品主图/商品主图_1.jpg", JPEG)
        bundle.writestr("重/商品数据.xlsx", heavy_sheet)
        bundle.writestr("重/商品主图/商品主图_1.jpg", JPEG)
    client = _client()
    _login(client)
    try:
        preview = client.post(
            "/admin/catalog/preview",
            data={"list_rate": "1", "sale_rate": "1"},
            files={"file": ("goods.zip", archive.getvalue(), "application/zip")},
            follow_redirects=False,
        )
        assert preview.status_code == 303
        assert client.app.state.db.execute(
            "select sku from products where sku in ('light-1', 'heavy-1')"
        ).fetchall() == []
        page = client.get("/admin/products")
        assert "轻夹" in page.text
        assert "重夹" in page.text
        assert "可上架 1 件，整件拦截 1 件" in page.text
        assert "$1.67" in page.text
        token = page.text.split('name="token" value="', 1)[1].split('"', 1)[0]
        again = client.post(
            "/admin/catalog/reprice",
            data={
                "token": token,
                "list_rate": "1",
                "sale_rate": "1",
                "grams_per_dollar": "15",
                "hold_percent": "300",
            },
            follow_redirects=False,
        )
        assert again.status_code == 303
        recalculated = client.get("/admin/products")
        assert "可上架 2 件，整件拦截 0 件" in recalculated.text
        assert "$3.33" in recalculated.text
        commit = client.post(
            "/admin/catalog/commit",
            data={
                "token": token,
                "list_rate": "1",
                "sale_rate": "1",
                "grams_per_dollar": "30",
                "hold_percent": "20",
            },
            follow_redirects=False,
        )
        assert commit.status_code == 303
        job = _finish(client)
        assert job["error"] == ""
        kept = client.app.state.db.execute("select image_url, listing from products where sku = 'light-1'").fetchone()
        blocked = client.app.state.db.execute("select image_url, listing, published from products where sku = 'heavy-1'").fetchone()
        assert kept["image_url"] == "/static/catalog/light-1/0.jpg"
        assert "拦截" not in kept["listing"]
        assert blocked["published"] == 0
        assert "拦截" in blocked["listing"]
        assert blocked["image_url"] == ""
        assert (light / "0.jpg").is_file()
        assert not heavy.exists()
    finally:
        shutil.rmtree(light, ignore_errors=True)
        shutil.rmtree(heavy, ignore_errors=True)


def test_preview_assembles_parallel_parts(monkeypatch):
    monkeypatch.delenv("DEEPL_AUTH_KEY", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    raw = _package()
    client = _client()
    _login(client)
    upload_id = "ab" * 8
    parts = [raw[:20], raw[20:45], raw[45:]]
    for index, chunk in enumerate(parts):
        sent = client.post(
            "/admin/catalog/part",
            data={"upload_id": upload_id, "index": str(index), "total": str(len(parts))},
            files={"chunk": ("part", chunk, "application/octet-stream")},
        )
        assert sent.status_code == 200
    done = client.post("/admin/catalog/assemble", data={"upload_id": upload_id})
    assert done.status_code == 200
    assert done.json()["ok"] is True
    page = client.get("/admin/products")
    assert "迷你挂历" in page.text
