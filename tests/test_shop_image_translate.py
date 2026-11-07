import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from shop.app import ROOT, create_app
from shop.image_translate import pending_images, storefront_image
from shop.staff import save_staff

SKU = "zz-img-test"
OTHER = "zz-img-other"


class FakeImages:
    def __init__(self):
        self.calls = []

    def translate(self, path, lang):
        self.calls.append((Path(path).name, lang))
        return b"\xff\xd8new"


def _client(fake):
    client = TestClient(create_app(units_per_usd=150, db_path=":memory:", image_client=fake))
    save_staff(client.app.state.db, "admin", "secret", "admin")
    client.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)
    return client


def _plant(sku, day):
    folder = ROOT / "static" / "catalog" / sku
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "0.jpg").write_bytes(b"\xff\xd8old")
    return folder


def _insert(client, sku, day):
    client.app.state.db.execute(
        """
        insert into products
            (sku, category, price_cents, stock, names, bullets, description, specs, image_url, source_zh, listing, published, offers, uploaded_at)
        values (?, 'kitchen', 500, 3, ?, '{}', ?, '{}', ?, '{}', '{}', 1, '[]', ?)
        """,
        (
            sku,
            '{"en":"Cup","ja":"Cup"}',
            '{"en":"Cup","ja":"Cup"}',
            f"/static/catalog/{sku}/0.jpg",
            day,
        ),
    )
    client.app.state.cache.delete("shop:catalog")


def test_storefront_uses_the_language_file_then_english(tmp_path):
    folder = tmp_path / "static" / "catalog" / "cup"
    folder.mkdir(parents=True)
    (folder / "0.jpg").write_bytes(b"old")
    url = "/static/catalog/cup/0.jpg"
    assert storefront_image(url, "ja", tmp_path) == url
    (folder / "en").mkdir()
    (folder / "en" / "0.jpg").write_bytes(b"en")
    assert storefront_image(url, "ja", tmp_path).endswith("/en/0.jpg")
    (folder / "ja").mkdir()
    (folder / "ja" / "0.jpg").write_bytes(b"ja")
    assert storefront_image(url, "ja", tmp_path).endswith("/ja/0.jpg")


def test_pending_images_include_every_untranslated_picture(tmp_path):
    cup = tmp_path / "static" / "catalog" / "cup"
    old = tmp_path / "static" / "catalog" / "old"
    cup.mkdir(parents=True)
    old.mkdir(parents=True)
    (cup / "0.jpg").write_bytes(b"old")
    (old / "0.jpg").write_bytes(b"older")
    rows = [
        {"sku": "cup", "uploaded_at": "2026-11-01", "image_url": "/static/catalog/cup/0.jpg", "listing": "{}", "offers": "[]"},
        {"sku": "old", "uploaded_at": "2026-01-01", "image_url": "/static/catalog/old/0.jpg", "listing": "{}", "offers": "[]"},
    ]
    tasks = pending_images(rows, tmp_path, "ja")
    assert [sku for sku, _path in tasks] == ["cup", "old"]
    (cup / "ja").mkdir()
    (cup / "ja" / "0.jpg").write_bytes(b"done")
    assert [sku for sku, _path in pending_images(rows, tmp_path, "ja")] == ["old"]


def test_manual_task_translates_one_language_for_the_chosen_days():
    folders = [_plant(SKU, "2026-11-01"), _plant(OTHER, "2026-01-01")]
    fake = FakeImages()
    try:
        client = _client(fake)
        _insert(client, SKU, "2026-11-01")
        _insert(client, OTHER, "2026-01-01")
        refused = client.post("/admin/images/translate", data={"lang": "de"})
        assert refused.status_code == 400
        assert fake.calls == []
        started = client.post(
            "/admin/images/translate",
            data={"lang": "ja"},
            follow_redirects=False,
        )
        assert started.status_code == 303
        client.app.state.image_thread.join(5)
        assert sorted(name for name, _lang in fake.calls) == ["0.jpg", "0.jpg"]
        assert (folders[0] / "ja" / "0.jpg").read_bytes() == b"\xff\xd8new"
        assert (folders[1] / "ja" / "0.jpg").read_bytes() == b"\xff\xd8new"
        assert not (folders[0] / "en").exists()
        page = client.get(f"/p/{SKU}?country=JP")
        assert f"/static/catalog/{SKU}/ja/0.jpg" in page.text
        admin = client.get("/admin/products")
        assert f'src="/static/catalog/{SKU}/0.jpg"' in admin.text
        again = client.post("/admin/images/translate", data={"lang": "ja"})
        assert again.status_code == 400
    finally:
        for folder in folders:
            shutil.rmtree(folder, ignore_errors=True)


def test_continue_skips_images_that_already_exist():
    folder = _plant(SKU, "2026-11-01")
    (folder / "1.jpg").write_bytes(b"\xff\xd8old")
    (folder / "ja").mkdir()
    (folder / "ja" / "0.jpg").write_bytes(b"\xff\xd8kept")
    other = _plant(OTHER, "2026-01-01")
    fake = FakeImages()
    try:
        client = _client(fake)
        client.app.state.db.execute(
            """
            insert into products
                (sku, category, price_cents, stock, names, bullets, description, specs, image_url, source_zh, listing, published, offers, uploaded_at)
            values (?, 'kitchen', 500, 3, ?, '{}', ?, '{}', ?, '{}', ?, 1, '[]', ?)
            """,
            (
                SKU,
                '{"en":"Cup","ja":"Cup"}',
                '{"en":"Cup","ja":"Cup"}',
                f"/static/catalog/{SKU}/0.jpg",
                '{"gallery":["/static/catalog/%s/0.jpg","/static/catalog/%s/1.jpg"]}' % (SKU, SKU),
                "2026-11-01",
            ),
        )
        _insert(client, OTHER, "2026-01-01")
        client.app.state.image_job.update(
            {
                "running": False,
                "lang": "ja",
                "date_from": "2026-11-01",
                "date_to": "2026-11-01",
                "done": 1,
                "total": 2,
                "error": "上次图片翻译中断了。",
            }
        )
        page = client.get("/admin/images")
        assert "继续未译的图" in page.text
        started = client.post("/admin/images/continue", follow_redirects=False)
        assert started.status_code == 303
        client.app.state.image_thread.join(5)
        assert ("1.jpg", "ja") in fake.calls
        assert (folder / "ja" / "0.jpg").read_bytes() == b"\xff\xd8kept"
        assert (folder / "ja" / "1.jpg").read_bytes() == b"\xff\xd8new"
        assert (other / "ja" / "0.jpg").read_bytes() == b"\xff\xd8new"
        done = client.post("/admin/images/continue")
        assert done.status_code == 400
        assert len(fake.calls) == 2
    finally:
        shutil.rmtree(folder, ignore_errors=True)
        shutil.rmtree(other, ignore_errors=True)


def test_image_translation_runs_several_pictures_at_once():
    import threading
    import time

    active = {"n": 0, "peak": 0}
    lock = threading.Lock()

    class Slow(FakeImages):
        def translate(self, path, lang):
            with lock:
                active["n"] += 1
                active["peak"] = max(active["peak"], active["n"])
            time.sleep(0.12)
            with lock:
                active["n"] -= 1
            return super().translate(path, lang)

    skus = [f"zz-img-fast-{index}" for index in range(4)]
    folders = [_plant(sku, "2026-11-01") for sku in skus]
    fake = Slow()
    try:
        client = _client(fake)
        for sku in skus:
            _insert(client, sku, "2026-11-01")
        started = client.post(
            "/admin/images/translate",
            data={"lang": "ja"},
            follow_redirects=False,
        )
        assert started.status_code == 303
        client.app.state.image_thread.join(5)
        assert active["peak"] >= 2
        assert len(fake.calls) == 4
    finally:
        for folder in folders:
            shutil.rmtree(folder, ignore_errors=True)


def test_picture_without_chinese_is_copied_and_not_sent(monkeypatch):
    monkeypatch.setattr("shop.app.image_has_cjk", lambda path: False)
    folder = _plant(SKU, "2026-11-01")
    fake = FakeImages()
    try:
        client = _client(fake)
        _insert(client, SKU, "2026-11-01")
        started = client.post("/admin/images/translate", data={"lang": "ja"}, follow_redirects=False)
        assert started.status_code == 303
        client.app.state.image_thread.join(5)
        assert fake.calls == []
        assert (folder / "ja" / "0.jpg").read_bytes() == b"\xff\xd8old"
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def test_sync_model_posts_without_the_async_header(monkeypatch, tmp_path):
    from shop.image_translate import MODEL, QwenImageClient

    image = tmp_path / "sku" / "0.jpg"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"\xff\xd8old")
    seen = {}

    class Response:
        def __init__(self, payload, status_code=200):
            self._payload = payload
            self.status_code = status_code
            self.content = b"\xff\xd8new"

        def json(self):
            return self._payload

        def raise_for_status(self):
            return None

    class Client:
        def __init__(self, timeout=None):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, headers=None, params=None, follow_redirects=False):
            if "uploads" in url:
                return Response({"data": {
                    "upload_dir": "dir",
                    "upload_host": "https://oss.example",
                    "oss_access_key_id": "k",
                    "signature": "s",
                    "policy": "p",
                    "x_oss_object_acl": "private",
                    "x_oss_forbid_overwrite": "true",
                }})
            return Response({})

        def post(self, url, headers=None, files=None, json=None):
            if "image-synthesis" in url:
                seen["headers"] = headers
                seen["model"] = json["model"]
            return Response({"output": {"image_url": "https://result.example/a.jpg"}})

    monkeypatch.setattr("shop.image_translate.httpx.Client", Client)
    monkeypatch.setattr("shop.image_translate._image_gate._sleep", lambda _seconds: None)
    body = QwenImageClient("sk-test", "ws").translate(image, "en")
    assert body == b"\xff\xd8new"
    assert seen["model"] == MODEL == "qwen-mt-image-2.0"
    assert "X-DashScope-Async" not in seen["headers"]
    assert seen["headers"]["X-DashScope-OssResourceResolve"] == "enable"


def test_image_translation_does_not_stop_text_translation():
    folder = _plant(SKU, "2026-11-01")
    fake = FakeImages()
    try:
        client = _client(fake)
        _insert(client, SKU, "2026-11-01")
        client.app.state.translate_job["running"] = True
        started = client.post("/admin/images/translate", data={"lang": "ja"}, follow_redirects=False)
        assert started.status_code == 303
        assert client.app.state.translate_job["running"] is True
        client.app.state.image_thread.join(5)
        blocked = client.post("/admin/catalog/publish", follow_redirects=False)
        assert blocked.status_code == 400
        assert "上一批翻译还在处理" in blocked.text
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def test_bulk_translate_counts_one_product_not_every_source_file():
    import io

    from PIL import Image

    class Editor:
        def edit(self, data, prompt):
            image = Image.new("RGB", (32, 32), (255, 255, 255))
            out = io.BytesIO()
            image.save(out, format="JPEG")
            return out.getvalue()

    sku = "zz-img-count"
    folder = ROOT / "static" / "catalog" / sku
    folder.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (32, 32), (10, 20, 30))
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    raw = buf.getvalue()
    (folder / "0.jpg").write_bytes(raw)
    (folder / "d0.jpg").write_bytes(raw)
    (folder / "c0.jpg").write_bytes(raw)
    client = TestClient(create_app(units_per_usd=150, db_path=":memory:", gen_editors=[Editor()]))
    save_staff(client.app.state.db, "admin", "secret", "admin")
    client.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)
    client.app.state.complete = lambda prompt, limit=0: ""
    client.app.state.writer = object()
    client.app.state.translator = object()
    client.app.state.db.execute("delete from products")
    try:
        client.app.state.db.execute(
            """
            insert into products
                (sku, category, price_cents, stock, names, bullets, description, specs, image_url, source_zh, listing, published, offers, uploaded_at)
            values (?, 'kitchen', 500, 3, ?, '{}', ?, '{}', ?, '{}', ?, 1, ?, '2026-11-07')
            """,
            (
                sku,
                '{"en":"Cup"}',
                '{"en":"Cup"}',
                f"/static/catalog/{sku}/0.jpg",
                '{"gallery":["/static/catalog/%s/0.jpg"],"detail_images":["/static/catalog/%s/d0.jpg"]}' % (sku, sku),
                '[{"id":"c","image":"/static/catalog/%s/c0.jpg"}]' % sku,
            ),
        )
        started = client.post("/admin/images/translate", data={"lang": "en"}, follow_redirects=False)
        assert started.status_code == 303
        client.app.state.image_thread.join(15)
        job = client.app.state.image_job
        assert job["total"] == 1
        assert job["done"] == 1
        assert job["result"]["kind"] == "story"
        assert (folder / "en" / "main" / "1.jpg").is_file()
        assert (folder / "en" / "main" / "3.jpg").is_file()
        assert not (folder / "en" / "main" / "4.jpg").exists()
        assert (folder / "en" / "story" / "1.jpg").is_file()
        assert (folder / "en" / "story" / "5.jpg").is_file()
        assert (folder / "c0.jpg").is_file()
        page = client.get("/admin/images")
        assert "还没有英文图" in page.text
        assert "还没出过这套图的商品" not in page.text
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def test_bulk_story_runs_products_side_by_side_and_keeps_a_landed_frame():
    import io
    import threading
    import time

    from PIL import Image

    state = {"peak_products": 0, "same": 0}
    lock = threading.Lock()
    busy = {}

    class Editor:
        def edit(self, data, prompt, size="1024x1024"):
            key = data[-24:]
            with lock:
                busy[key] = busy.get(key, 0) + 1
                state["same"] = max(state["same"], busy[key])
                state["peak_products"] = max(state["peak_products"], sum(1 for n in busy.values() if n))
            time.sleep(0.05)
            with lock:
                busy[key] -= 1
            image = Image.new("RGB", (32, 32), (255, 255, 255))
            out = io.BytesIO()
            image.save(out, format="JPEG")
            return out.getvalue()

    folders = []
    client = TestClient(create_app(units_per_usd=150, db_path=":memory:", gen_editors=[Editor()]))
    save_staff(client.app.state.db, "admin", "secret", "admin")
    client.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)
    client.app.state.complete = lambda prompt, limit=0: ""
    client.app.state.writer = object()
    client.app.state.translator = object()
    client.app.state.db.execute("delete from products")
    client.app.state.db.execute(
        "insert into settings (key, value) values ('gen_api_workers', '2')"
    )
    try:
        for index, sku in enumerate(("zz-lane-a", "zz-lane-b")):
            folder = ROOT / "static" / "catalog" / sku
            folder.mkdir(parents=True, exist_ok=True)
            folders.append(folder)
            image = Image.new("RGB", (32, 32), (index * 40, 10, 20))
            buf = io.BytesIO()
            image.save(buf, format="JPEG")
            (folder / "0.jpg").write_bytes(buf.getvalue())
            (folder / "en" / "main").mkdir(parents=True, exist_ok=True)
            if index == 0:
                (folder / "en" / "main" / "1.jpg").write_bytes(b"already-landed")
            client.app.state.db.execute(
                """
                insert into products
                    (sku, category, price_cents, stock, names, bullets, description, specs, image_url, source_zh, listing, published, offers, uploaded_at)
                values (?, 'kitchen', 500, 3, '{}', '{}', '{}', '{}', ?, '{}', '{}', 1, '[]', '2026-11-07')
                """,
                (sku, "/static/catalog/%s/0.jpg" % sku),
            )
        started = client.post("/admin/images/translate", data={"lang": "en"}, follow_redirects=False)
        assert started.status_code == 303
        client.app.state.image_thread.join(30)
        assert state["peak_products"] >= 2
        assert state["same"] == 1
        assert (folders[0] / "en" / "main" / "1.jpg").read_bytes() == b"already-landed"
        assert (folders[0] / "en" / "main" / "3.jpg").is_file()
        assert (folders[0] / "en" / "story" / "5.jpg").is_file()
        assert (folders[1] / "en" / "main" / "1.jpg").is_file()
        job = client.app.state.image_job
        assert job["total"] == 2
        assert job["done"] == 2
    finally:
        for folder in folders:
            shutil.rmtree(folder, ignore_errors=True)


def test_one_sku_translation_leaves_the_other_product():
    folders = [_plant(SKU, "2026-11-01"), _plant(OTHER, "2026-01-01")]
    fake = FakeImages()
    try:
        client = _client(fake)
        _insert(client, SKU, "2026-11-01")
        _insert(client, OTHER, "2026-01-01")
        missing = client.post("/admin/images/translate/one", data={"lang": "ja", "sku": ""})
        assert missing.status_code == 400
        assert fake.calls == []
        started = client.post(
            "/admin/images/translate/one",
            data={"lang": "ja", "sku": SKU},
            follow_redirects=False,
        )
        assert started.status_code == 303
        client.app.state.image_thread.join(5)
        assert fake.calls == [("0.jpg", "ja")]
        assert (folders[0] / "ja" / "0.jpg").read_bytes() == b"\xff\xd8new"
        assert not (folders[1] / "ja").exists()
    finally:
        for folder in folders:
            shutil.rmtree(folder, ignore_errors=True)
