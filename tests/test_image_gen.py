import io
import json
import threading
import time
from threading import Lock

from fastapi.testclient import TestClient
from PIL import Image

from shop.app import create_app
from shop.gen_connect import parse_ssh
from shop.db import connect, migrate
from shop.image_gen import (
    DETAIL_PROMPT,
    HERO_PROMPT,
    CommerceImageClient,
    GenError,
    commerce_prompt,
    fit_size,
    generate_details,
    generate_story,
    missing_story_slots,
    story_fact_sheet,
    story_panel_facts,
    story_panels,
    story_prompt,
    claim_task,
    enqueue,
    finish_task,
    generate_product,
    pending_rows,
    plan_queue,
    redraws_product,
    spread,
    stamp_label,
    task_progress,
)
from shop.staff import save_staff


class Editor:
    def __init__(self):
        self.prompts = []
        self.lock = Lock()

    def edit(self, data, prompt):
        with self.lock:
            self.prompts.append(prompt)
        image = Image.new("RGB", (800, 800), (255, 255, 255))
        out = io.BytesIO()
        image.save(out, format="JPEG")
        return out.getvalue()


def _jpeg():
    image = Image.new("RGB", (40, 30), (20, 40, 60))
    out = io.BytesIO()
    image.save(out, format="JPEG")
    return out.getvalue()


def _row(conn, sku, offers, gen_at=""):
    folder_url = f"/static/catalog/{sku}/c0.jpg"
    conn.execute(
        """
        insert into products
            (sku, category, price_cents, stock, names, bullets, description, specs, image_url, offers, gen_at)
        values (?, 'kitchen', 500, 3, '{}', '{}', '{}', '{}', ?, ?, ?)
        """,
        (sku, folder_url, json.dumps(offers), gen_at),
    )


def test_hero_prompt_recomposes_the_frame():
    assert "80%" in HERO_PROMPT
    assert "center" in HERO_PROMPT
    assert "contact shadow" in HERO_PROMPT
    assert "Do not add any text" in HERO_PROMPT
    assert "Do not keep the original crop" in HERO_PROMPT
    assert "比例" not in HERO_PROMPT


def test_color_labels_redraw_and_sizes_keep_the_product():
    assert redraws_product("Agate Green")
    assert redraws_product("Knight Black")
    assert redraws_product("Twilight Black + Cherry Pink")
    assert redraws_product("樱花粉+深灰色")
    assert not redraws_product("Twilight Black + Twilight Black")
    assert not redraws_product("4个装")
    assert not redraws_product("超值四件套")
    assert not redraws_product("Pack of 4 – 6cm")
    assert not redraws_product("Heavy-Duty – Black – Pack of 4 – 8cm")


def test_sku_text_sits_in_the_bottom_right():
    stamped = stamp_label(_jpeg(), "Agate Green")
    image = Image.open(io.BytesIO(stamped)).convert("RGB")
    assert image.size == (800, 800)
    assert image.getpixel((20, 20)) == (255, 255, 255)
    corner = image.crop((520, 640, 790, 790)).getdata()
    assert any(pixel != (255, 255, 255) for pixel in corner)


def test_a_finished_product_is_not_run_again(tmp_path):
    conn = connect(":memory:")
    migrate(conn)
    sku = "cup"
    _row(
        conn,
        sku,
        [
            {"id": "a", "source_label": "Agate Green", "label": "", "image": f"/static/catalog/{sku}/green.jpg"},
            {"id": "b", "source_label": "Pack of 4 – 6cm", "label": "", "image": ""},
            {"id": "c", "source_label": "Knight Black", "label": "", "image": f"/static/catalog/{sku}/c0.jpg"},
        ],
    )
    folder = tmp_path / "static" / "catalog" / sku
    folder.mkdir(parents=True)
    (folder / "c0.jpg").write_bytes(_jpeg())
    (folder / "green.jpg").write_bytes(_jpeg())
    (folder / "en" / "main").mkdir(parents=True)
    (folder / "en" / "main" / "4.jpg").write_bytes(b"old-fourth")
    editor = Editor()
    generate_product(conn, tmp_path, sku, editor, tmp_path / "backup")
    row = conn.execute("select image_url, offers, gen_at from products where sku = ?", (sku,)).fetchone()
    assert row["gen_at"]
    original = (folder / "c0.jpg").read_bytes()
    assert row["image_url"].endswith("/c0.jpg")
    fourth = folder / "en" / "main" / "4.jpg"
    assert fourth.is_file()
    assert fourth.read_bytes() not in {original, b"old-fourth"}
    assert (folder / "c0.jpg").read_bytes() == original
    offers = json.loads(row["offers"])
    assert offers[0]["image"].endswith("/green.jpg")
    assert offers[1]["image"].endswith("/c0.jpg")
    assert offers[2]["image"].endswith("/c0.jpg")
    hero_file = tmp_path / "static" / row["image_url"][len("/static/"):]
    size_file = tmp_path / "static" / offers[1]["image"][len("/static/"):]
    assert size_file.read_bytes() == hero_file.read_bytes()
    assert any("Agate Green" in prompt for prompt in editor.prompts)
    assert sum("Pack of 4" in prompt for prompt in editor.prompts) == 0
    assert sum("Knight Black" in prompt for prompt in editor.prompts) == 0
    assert all("caption" in prompt or "Do not add any text" in prompt for prompt in editor.prompts)
    try:
        generate_product(conn, tmp_path, sku, editor, tmp_path / "backup")
    except GenError as exc:
        assert "不会再跑" in str(exc)
    else:
        raise AssertionError("marked product ran again")


def test_a_failed_color_stays_saved_and_retries_only_itself(tmp_path):
    conn = connect(":memory:")
    migrate(conn)
    sku = "mask"
    _row(
        conn,
        sku,
        [
            {"id": "green", "source_label": "Agate Green", "label": "", "image": f"/static/catalog/{sku}/green.jpg"},
            {"id": "pair", "source_label": "Agate Green + Knight Black", "label": "", "image": f"/static/catalog/{sku}/pair.jpg"},
            {"id": "pack", "source_label": "4个装", "label": "", "image": f"/static/catalog/{sku}/pack.jpg"},
        ],
    )
    folder = tmp_path / "static" / "catalog" / sku
    folder.mkdir(parents=True)
    (folder / "c0.jpg").write_bytes(_jpeg())
    (folder / "green.jpg").write_bytes(_jpeg())
    (folder / "pair.jpg").write_bytes(_jpeg())
    (folder / "pack.jpg").write_bytes(_jpeg())

    class Flaky(Editor):
        def __init__(self):
            super().__init__()
            self.pair_calls = 0

        def edit(self, data, prompt):
            if "Agate Green + Knight Black" in prompt:
                self.pair_calls += 1
                if self.pair_calls == 1:
                    raise GenError("这张没出成")
            return super().edit(data, prompt)

    editor = Flaky()
    try:
        generate_product(conn, tmp_path, sku, editor, tmp_path / "backup")
    except GenError as exc:
        assert "只补失败的" in str(exc)
    else:
        raise AssertionError("failed color was treated as success")
    row = conn.execute("select image_url, offers, gen_at from products where sku = ?", (sku,)).fetchone()
    assert row["gen_at"]
    offers = json.loads(row["offers"])
    assert offers[0]["generated"] == 1
    assert offers[1].get("generated") != 1
    assert offers[2].get("generated") != 1
    assert "pack" not in "".join(editor.prompts).lower() or "4个装" not in "".join(editor.prompts)
    assert sum("4个装" in prompt for prompt in editor.prompts) == 0
    generate_product(conn, tmp_path, sku, editor, tmp_path / "backup")
    row = conn.execute("select offers from products where sku = ?", (sku,)).fetchone()
    offers = json.loads(row["offers"])
    assert offers[1]["generated"] == 1
    assert editor.pair_calls == 2
    assert sum("Agate Green" in prompt and "Knight" not in prompt for prompt in editor.prompts) == 1


def test_plan_lists_what_will_generate_and_what_is_skipped():
    conn = connect(":memory:")
    migrate(conn)
    sku = "cup"
    _row(
        conn,
        sku,
        [
            {"id": "a", "source_label": "Agate Green", "label": "", "image": f"/static/catalog/{sku}/green.jpg"},
            {"id": "b", "source_label": "4个装", "label": "", "image": f"/static/catalog/{sku}/pack.jpg"},
            {"id": "c", "source_label": "Twilight Black + Twilight Black", "label": "", "image": f"/static/catalog/{sku}/pair.jpg"},
            {"id": "d", "source_label": "Twilight Black + Cherry Pink", "label": "", "image": f"/static/catalog/{sku}/mix.jpg"},
            {"id": "e", "source_label": "Knight Black", "label": "", "image": f"/static/catalog/{sku}/c0.jpg"},
        ],
    )
    row = conn.execute(
        "select sku, image_url, listing, offers, gen_at from products where sku = ?",
        (sku,),
    ).fetchone()
    from shop.image_gen import plan_product
    plan = {item["label"]: item for item in plan_product(row)}
    assert plan["主图"]["action"] == "generate"
    assert plan["Agate Green"]["action"] == "generate"
    assert plan["Twilight Black + Cherry Pink"]["action"] == "generate"
    assert plan["4个装"]["action"] == "skip"
    assert plan["Twilight Black + Twilight Black"]["action"] == "skip"
    assert plan["Knight Black"]["action"] == "skip"


def test_four_cards_split_the_remaining_products():
    conn = connect(":memory:")
    migrate(conn)
    for index in range(8):
        _row(conn, f"p{index}", [])
    _row(conn, "done", [], gen_at="2026-11-04")
    rows = conn.execute("select sku, image_url, listing, gen_at from products").fetchall()
    pending = [row["sku"] for row in pending_rows(rows)]
    assert "done" not in pending
    assert len(pending) == 8
    editors = [Editor() for _ in range(4)]

    def work(editor, sku):
        editor.edit(b"\xff\xd8", HERO_PROMPT)
        editor.skus = getattr(editor, "skus", [])
        editor.skus.append(sku)

    spread(pending, editors, work)
    counts = [len(getattr(editor, "skus", [])) for editor in editors]
    assert sum(counts) == 8
    assert all(count > 0 for count in counts)


def test_a_second_card_takes_the_next_task_and_progress_survives_a_reread():
    conn = connect(":memory:")
    migrate(conn)
    assert enqueue(conn, ["a", "b", "c"]) == 3
    assert claim_task(conn, "gpu-1") == "a"
    assert claim_task(conn, "gpu-2") == "b"
    finish_task(conn, "a", True)
    progress = task_progress(conn)
    assert progress["result"]["done"] == 1
    assert progress["pending"] == 1
    assert progress["active"] == 1
    assert progress["total"] == 3
    assert task_progress(conn) == progress
    assert enqueue(conn, ["a", "b", "c"]) == 0


def test_refresh_still_shows_the_queue():
    client = TestClient(create_app(units_per_usd=150, db_path=":memory:", gen_editors=[Editor()]))
    save_staff(client.app.state.db, "admin", "secret", "admin")
    client.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)
    client.post("/admin/images/gen/pause", data={"paused": "1"}, follow_redirects=False)
    enqueue(client.app.state.db, ["queued-sku"])
    page = client.get("/admin/images")
    assert "已完成 0 / 1" in page.text
    assert "还剩 1" in page.text
    progress = client.get("/admin/images/gen/progress").json()
    assert progress["total"] == 1
    assert progress["pending"] == 1
    assert progress["result"]["done"] == 0


def test_plan_queue_counts_calls_and_skips():
    conn = connect(":memory:")
    migrate(conn)
    _row(conn, "color", [{"label": "樱花粉", "image": "/static/catalog/color/c1.jpg"}])
    _row(conn, "pack", [{"label": "4个装", "image": "/static/catalog/pack/c1.jpg"}])
    assert enqueue(conn, ["color", "pack"]) == 2
    plan = plan_queue(conn)
    by_sku = {item["sku"]: item for item in plan["items"]}
    assert plan["calling"] == 2
    assert plan["shots"] == 3
    assert by_sku["color"]["generate"] == 2
    assert by_sku["pack"]["generate"] == 1
    assert "4个装" not in by_sku["pack"]["note"]


def test_resume_claims_a_product_that_needs_no_new_call():
    editor = Editor()
    client = TestClient(create_app(units_per_usd=150, db_path=":memory:", gen_editors=[editor]))
    save_staff(client.app.state.db, "admin", "secret", "admin")
    client.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)
    client.post("/admin/images/gen/pause", data={"paused": "1"}, follow_redirects=False)
    client.app.state.db.execute(
        """
        insert into products
            (sku, category, price_cents, stock, names, bullets, description, specs, image_url, offers, gen_at)
        values ('settled', 'kitchen', 500, 1, '{}', '{}', '{}', '{}', '/static/catalog/settled/c0.jpg', '[]', '2026-11-07')
        """
    )
    enqueue(client.app.state.db, ["settled"])
    client.post("/admin/images/gen/pause", data={"paused": "0"}, follow_redirects=False)
    status = ""
    for _ in range(30):
        row = client.app.state.db.execute("select status from gen_tasks where sku = 'settled'").fetchone()
        status = row["status"]
        if status == "done":
            break
        time.sleep(0.1)
    assert status == "done"
    assert editor.prompts == []


def test_pause_stops_new_images_until_resumed():
    client = TestClient(create_app(units_per_usd=150, db_path=":memory:", gen_editors=[Editor()]))
    save_staff(client.app.state.db, "admin", "secret", "admin")
    client.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)
    page = client.get("/admin/images")
    assert "暂停生图" in page.text
    client.post("/admin/images/gen/pause", data={"paused": "1"}, follow_redirects=False)
    paused = client.get("/admin/images")
    assert "生图已暂停" in paused.text
    assert "继续生图" in paused.text
    client.app.state.db.execute(
        """
        insert into products
            (sku, category, price_cents, stock, names, bullets, description, specs, image_url)
        values ('fresh', 'kitchen', 500, 1, '{}', '{}', '{}', '{}', '/static/catalog/fresh/c0.jpg')
        """
    )
    blocked = client.post("/admin/images/gen/rest")
    assert blocked.status_code == 400
    assert "已暂停" in blocked.text
    accepted = client.post("/admin/images/gen/one", data={"sku": "fresh"}, follow_redirects=False)
    assert accepted.status_code == 303
    enqueue(client.app.state.db, ["other"])
    time.sleep(0.6)
    row = client.app.state.db.execute("select status from gen_tasks where sku = 'fresh'").fetchone()
    assert row["status"] in ("running", "done", "failed")
    other = client.app.state.db.execute("select status from gen_tasks where sku = 'other'").fetchone()
    assert other["status"] == "pending"
    progress = client.get("/admin/images/gen/progress").json()
    assert progress["paused"] is True
    client.post("/admin/images/gen/pause", data={"paused": "0"}, follow_redirects=False)
    assert "暂停生图" in client.get("/admin/images").text


def test_admin_has_the_two_run_buttons_and_skips_a_marked_product():
    client = TestClient(create_app(units_per_usd=150, db_path=":memory:", gen_editors=[Editor()]))
    save_staff(client.app.state.db, "admin", "secret", "admin")
    client.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)
    page = client.get("/admin/images")
    products = client.get("/admin/products")
    assert "生成这一件" in page.text
    assert "欧美电商图" in page.text
    assert "翻译这一件" in page.text
    assert "生成这一件详情" in page.text
    assert "生成这件详情" not in page.text
    assert "跑剩余所有商品" in page.text
    assert "出图列表" in page.text
    assert "待生成" in page.text
    assert "图片 API" in page.text
    assert 'name="gen_api_key"' in page.text
    assert 'name="gen_api_url"' in page.text
    assert "再加一张显卡" not in page.text
    assert "连接这张卡" not in page.text
    assert 'name="ssh_password"' not in page.text
    assert 'name="gen_token"' not in page.text
    assert "图片翻译" not in products.text
    assert "商品图生成" not in products.text
    client.app.state.db.execute(
        """
        insert into products
            (sku, category, price_cents, stock, names, bullets, description, specs, image_url, gen_at)
        values ('marked', 'kitchen', 500, 1, '{}', '{}', '{}', '{}', '/static/catalog/marked/c0.jpg', '2026-11-04')
        """
    )
    again = client.post("/admin/images/gen/one", data={"sku": "marked"}, follow_redirects=False)
    assert again.status_code == 400
    assert "已经出过图" in again.text
    kept = client.app.state.db.execute("select gen_at from products where sku = 'marked'").fetchone()
    assert str(kept["gen_at"] or "").strip() == "2026-11-04"
    missing = client.post("/admin/images/gen/one", data={"sku": ""})
    assert "先填写要跑的货号" in missing.text


def test_a_pasted_ssh_line_is_split_before_connect():
    assert parse_ssh("ssh -p 41135 root@connect.westb.seetacloud.com", "41125", "root") == (
        "connect.westb.seetacloud.com",
        "41135",
        "root",
    )
    seen = []

    def connector(**kwargs):
        seen.append(kwargs)
        return "已连上。这张卡会自动领还没出的图。"

    client = TestClient(create_app(units_per_usd=150, db_path=":memory:", gen_editors=[Editor()], gen_connector=connector))
    save_staff(client.app.state.db, "admin", "secret", "admin")
    client.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)
    page = client.post(
        "/admin/images/gen/connect",
        data={
            "public_url": "https://gpu.example.com:8443",
            "ssh_host": "ssh -p 41135 root@connect.westb.seetacloud.com",
            "ssh_port": "41125",
            "ssh_user": "root",
            "ssh_password": "gpu-secret-1",
        },
    )
    assert seen[0]["host"] == "connect.westb.seetacloud.com"
    assert seen[0]["port"] == "41135"
    assert "gpu-secret-1" not in page.text


def test_one_click_connects_a_card_and_hides_the_password():
    seen = []

    def connector(**kwargs):
        seen.append(kwargs)
        if kwargs["password"] != "gpu-secret-1":
            raise AssertionError("password was not kept")
        return "已连上。这张卡会自动领还没出的图。"

    client = TestClient(create_app(units_per_usd=150, db_path=":memory:", gen_editors=[Editor()], gen_connector=connector))
    save_staff(client.app.state.db, "admin", "secret", "admin")
    client.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)
    missing = client.post("/admin/images/gen/connect", data={"public_url": "", "ssh_host": ""})
    assert missing.status_code == 400
    assert "公网地址填自定义服务那条 https" in missing.text
    page = client.post(
        "/admin/images/gen/connect",
        data={
            "public_url": "https://gpu.example.com:8443",
            "ssh_host": "connect.westb.seetacloud.com",
            "ssh_port": "41125",
            "ssh_user": "root",
            "ssh_password": "gpu-secret-1",
        },
    )
    assert page.status_code == 200
    assert "gpu-secret-1" not in page.text
    assert seen[0]["public_url"] == "https://gpu.example.com:8443"
    again = client.post(
        "/admin/images/gen/connect",
        data={
            "public_url": "https://gpu.example.com:8443",
            "ssh_host": "connect.westb.seetacloud.com",
            "ssh_port": "41125",
            "ssh_user": "root",
            "ssh_password": "",
        },
    )
    assert seen[1]["password"] == "gpu-secret-1"
    stored = client.app.state.db.execute("select value from settings where key = 'gen_workers'").fetchone()["value"]
    assert "https://gpu.example.com:8443" in stored
    kept = client.post(
        "/admin/images/gen/connect",
        data={
            "public_url": "https://gpu.example.com:8443",
            "ssh_host": "connect.westb.seetacloud.com",
            "ssh_port": "41125",
            "ssh_user": "root",
            "ssh_password": "",
        },
    )
    assert kept.status_code == 200
    fresh = TestClient(create_app(units_per_usd=150, db_path=":memory:", gen_editors=[Editor()]))
    save_staff(fresh.app.state.db, "admin", "secret", "admin")
    fresh.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)
    fresh.app.state.db.execute(
        "insert into settings (key, value) values ('gen_workers', ?)",
        ('["https://u1192984-99f9-9fba5459.westb.seetacloud.com:8443"]',),
    )
    restored = fresh.get("/admin/images")
    assert "再加一张显卡" not in restored.text
    typed = fresh.post(
        "/admin/images/gen/connect",
        data={
            "public_url": "https://u1192984-99f9-9fba5459.westb.seetacloud.com:8443",
            "ssh_host": "connect.westb.seetacloud.com",
            "ssh_port": "41125",
            "ssh_user": "root",
            "ssh_password": "",
        },
    )
    assert typed.status_code == 200
    assert "gpu-secret-1" not in typed.text


def test_delete_card_removes_only_that_card():
    client = TestClient(create_app(units_per_usd=150, db_path=":memory:", gen_editors=[Editor()]))
    save_staff(client.app.state.db, "admin", "secret", "admin")
    client.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)
    links = [
        {
            "url": "https://old.example.com:8443",
            "host": "connect.westb.seetacloud.com",
            "port": "41135",
            "user": "root",
            "password": "old-secret",
            "ok": False,
            "detail": "没连上",
        },
        {
            "url": "https://new.example.com:8443",
            "host": "connect.westb.seetacloud.com",
            "port": "16238",
            "user": "root",
            "password": "new-secret",
            "ok": True,
            "detail": "已连上。",
        },
    ]
    client.app.state.db.execute(
        "insert into settings (key, value) values ('gen_links', ?)",
        (json.dumps(links),),
    )
    client.app.state.db.execute(
        "insert into settings (key, value) values ('gen_workers', ?)",
        ('["https://new.example.com:8443"]',),
    )
    page = client.get("/admin/images")
    assert "删除这张卡" not in page.text
    gone = client.post(
        "/admin/images/gen/remove",
        data={
            "public_url": "https://old.example.com:8443",
            "ssh_host": "connect.westb.seetacloud.com",
            "ssh_port": "41135",
            "ssh_user": "root",
        },
    )
    assert gone.status_code == 200
    assert "old-secret" not in gone.text
    assert "new-secret" not in gone.text
    stored = json.loads(client.app.state.db.execute("select value from settings where key = 'gen_links'").fetchone()["value"])
    assert [item["port"] for item in stored] == ["16238"]
    workers = client.app.state.db.execute("select value from settings where key = 'gen_workers'").fetchone()["value"]
    assert "https://new.example.com:8443" in workers
    assert "old.example.com" not in workers
    blank = client.post(
        "/admin/images/gen/remove",
        data={"public_url": "", "ssh_host": "", "ssh_port": "41125", "ssh_user": "root"},
    )
    assert blank.status_code == 200


def test_api_editor_posts_edits(monkeypatch):
    from shop.image_gen import ApiEditor, GenError
    import base64
    import io
    from PIL import Image

    calls = []

    class FakeResponse:
        def __init__(self, status_code, payload=None, content=b""):
            self.status_code = status_code
            self._payload = payload or {}
            self.content = content
            self.text = ""

        def json(self):
            return self._payload

        def raise_for_status(self):
            if self.status_code >= 400:
                raise GenError("http")

    def fake_post(url, data=None, files=None, headers=None, timeout=None):
        calls.append({"url": url, "data": data, "files": files, "headers": headers})
        image = Image.new("RGB", (64, 64), (10, 20, 30))
        out = io.BytesIO()
        image.save(out, format="JPEG")
        return FakeResponse(200, {"status": "completed", "data": [{"b64_json": base64.b64encode(out.getvalue()).decode("ascii")}]})

    monkeypatch.setattr("shop.image_gen.httpx.post", fake_post)
    editor = ApiEditor("https://agent3.shyfai.cn", "sk-test", "gpt-image-2")
    raw = editor.edit(b"\xff\xd8\xff", "keep product on white")
    assert raw.startswith(b"\xff\xd8")
    assert calls[0]["url"].endswith("/v1/images/edits")
    assert calls[0]["headers"]["Authorization"] == "Bearer sk-test"
    assert calls[0]["data"]["model"] == "gpt-image-2"
    assert calls[0]["data"]["size"] == "1024x1024"
    wide = editor.edit(b"\xff\xd8\xff", "detail", size="1024x4096")
    assert wide.startswith(b"\xff\xd8")
    assert calls[1]["data"]["size"] == "1024x4096"

    client = TestClient(create_app(units_per_usd=150, db_path=":memory:", gen_editors=[Editor()]))
    save_staff(client.app.state.db, "admin", "secret", "admin")
    client.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)
    saved = client.post(
        "/admin/images/gen/api",
        data={
            "gen_api_url": "https://agent3.shyfai.cn",
            "gen_api_key": "sk-live-example",
            "gen_api_model": "gpt-image-2",
            "gen_api_workers": "3",
        },
        follow_redirects=True,
    )
    assert saved.status_code == 200
    assert "生图 API 已保存" in saved.text or "sk-live-example" not in saved.text
    row = client.app.state.db.execute("select value from settings where key='gen_api_key'").fetchone()
    assert row["value"] == "sk-live-example"
    workers = client.app.state.db.execute("select value from settings where key='gen_api_workers'").fetchone()["value"]
    assert workers == "3"


def test_detail_image_uses_the_original_shape_and_is_saved_once(tmp_path):
    assert fit_size(800, 3200) == "1024x4096"
    assert fit_size(1000, 1000) == "1024x1024"
    folder = tmp_path / "static" / "catalog" / "cup"
    folder.mkdir(parents=True)
    image = Image.new("RGB", (800, 3200), (20, 40, 60))
    out = io.BytesIO()
    image.save(out, format="JPEG")
    (folder / "d0.jpg").write_bytes(out.getvalue())
    conn = connect(str(tmp_path / "shop.sqlite"))
    migrate(conn)
    conn.execute(
        """
        insert into products
            (sku, category, price_cents, stock, names, bullets, description, specs, image_url, listing)
        values ('cup', 'kitchen', 500, 1, '{}', '{}', '{}', '{}', '/static/catalog/cup/c0.jpg', ?)
        """,
        (json.dumps({"detail_images": ["/static/catalog/cup/d0.jpg"]}),),
    )

    class DetailEditor:
        def __init__(self):
            self.calls = []

        def edit(self, data, prompt, size="1024x1024"):
            self.calls.append((prompt, size))
            made = Image.new("RGB", (32, 128), (255, 255, 255))
            buf = io.BytesIO()
            made.save(buf, format="JPEG")
            return buf.getvalue()

    editor = DetailEditor()
    assert generate_details(conn, tmp_path, "cup", editor, workers=1) == 1
    assert editor.calls == [(DETAIL_PROMPT, "1024x4096")]
    saved = folder / "en" / "d0.jpg"
    assert saved.is_file()
    assert saved.read_bytes().startswith(b"\xff\xd8")
    try:
        generate_details(conn, tmp_path, "cup", editor, workers=1)
    except GenError as exc:
        assert "不会再出" in str(exc)
    else:
        raise AssertionError("saved detail was generated again")
    assert len(editor.calls) == 1


def test_story_keeps_a_mixed_color_label_and_draws_five_details():
    sheet = story_fact_sheet("gloves", "38cm", "乳胶 厨房使用 注意清洗", ["红色+蓝色"])
    assert "红色+蓝色" in sheet
    assert "not two products" in sheet
    titles = ["Hero", "Use", "Specs", "Construction", "Second detail"]
    panels = story_panels("乳胶手套 38cm 厨房使用 注意清洗")
    assert [panel["title"] for panel in panels] == titles
    assert [panel["index"] for panel in panels] == [1, 2, 3, 4, 5]
    plain = story_panels("plain glove")
    assert [panel["title"] for panel in plain] == titles
    assert all(panel["title"] != "Care" for panel in panels)


def test_story_keeps_a_counted_set_together():
    notes = "Portable ear spoon 6-piece set\nPU leather case for storage"
    facts = story_panel_facts(
        {"title": "Specs", "task": "One large number"},
        "Ear set",
        "Material: steel\nWeight: 0.0132kg",
        notes,
    )
    assert "6-piece" in facts
    prompt = story_prompt("en", facts, {"title": "Specs", "task": "One large number"}, [])
    assert "whole set" in prompt
    assert "visible in it" in prompt
    close = story_prompt("en", facts, {"title": "Construction", "task": "close-up"}, [])
    assert "one piece of the set" in close


def test_story_keeps_the_other_images_when_one_reply_is_text(tmp_path):
    from shop.image_gen import _write_jobs

    folder = tmp_path / "main"

    class Editor:
        def edit(self, data, prompt, size="1024x1024"):
            if "skip" in prompt:
                raise GenError("生图接口错误：目前无法在此对话中直接生成或编辑图片，整理成生图指令")
            made = Image.new("RGB", (8, 8), (255, 255, 255))
            buf = io.BytesIO()
            made.save(buf, format="JPEG")
            return buf.getvalue()

    try:
        _write_jobs(
            Editor(),
            b"ref",
            [(folder, 1, "keep", "1024x1024"), (folder, 2, "skip this", "1024x1024")],
            None,
            done=0,
            total=2,
        )
    except GenError as exc:
        assert "其余已落盘" in str(exc)
    else:
        raise AssertionError("text reply was treated as a finished image")
    assert (folder / "1.jpg").is_file()
    assert not (folder / "2.jpg").exists()


def test_story_keeps_images_when_the_reply_says_chat(tmp_path):
    from shop.image_gen import _write_jobs

    folder = tmp_path / "main"

    class Editor:
        def edit(self, data, prompt, size="1024x1024"):
            if "skip" in prompt:
                raise GenError("生图接口错误：目前无法在此聊天中直接生成图片，但可以为你整理英文提示词")
            made = Image.new("RGB", (8, 8), (255, 255, 255))
            buf = io.BytesIO()
            made.save(buf, format="JPEG")
            return buf.getvalue()

    try:
        _write_jobs(
            Editor(),
            b"ref",
            [(folder, 1, "keep", "1024x1024"), (folder, 2, "skip this", "1024x1024")],
            None,
            done=0,
            total=2,
        )
    except GenError as exc:
        assert "其余已落盘" in str(exc)
    else:
        raise AssertionError("chat reply was treated as a hard failure")
    assert (folder / "1.jpg").is_file()
    assert not (folder / "2.jpg").exists()


def test_story_retries_when_the_upstream_drops_one_image(tmp_path, monkeypatch):
    from shop import image_gen
    from shop.image_gen import _write_jobs

    monkeypatch.setattr(image_gen, "_UPSTREAM_PAUSE", 0)
    folder = tmp_path / "main"
    calls = {"n": 0, "drop": 0}
    gate = threading.Lock()

    class Editor:
        def edit(self, data, prompt, size="1024x1024"):
            with gate:
                calls["n"] += 1
                if "drop" in prompt:
                    calls["drop"] += 1
                    fail = calls["drop"] == 1
                else:
                    fail = False
            if fail:
                raise GenError("生图接口错误：Upstream request failed")
            made = Image.new("RGB", (8, 8), (255, 255, 255))
            buf = io.BytesIO()
            made.save(buf, format="JPEG")
            return buf.getvalue()

    count = _write_jobs(
        Editor(),
        b"ref",
        [(folder, 1, "keep", "1024x1024"), (folder, 2, "drop this", "1024x1024")],
        None,
        done=0,
        total=2,
        workers=4,
    )
    assert count == 2
    assert calls["n"] >= 3
    assert (folder / "1.jpg").is_file()
    assert (folder / "2.jpg").is_file()


def test_story_draws_a_set_at_the_detail_size(tmp_path):
    folder = tmp_path / "static" / "catalog" / "cup"
    folder.mkdir(parents=True)
    image = Image.new("RGB", (80, 80), (20, 40, 60))
    out = io.BytesIO()
    image.save(out, format="JPEG")
    (folder / "0.jpg").write_bytes(out.getvalue())
    conn = connect(str(tmp_path / "shop.sqlite"))
    migrate(conn)
    conn.execute(
        """
        insert into products
            (sku, category, price_cents, stock, names, bullets, description, specs, image_url, listing, offers)
        values ('cup', 'kitchen', 500, 1, ?, '{}', '{}', '{}', '/static/catalog/cup/0.jpg', ?, ?)
        """,
        (
            json.dumps({"en": "Dish gloves"}),
            json.dumps({"detail_images": ["/static/catalog/cup/0.jpg"]}),
            json.dumps([{"id": "a", "label": "红色+蓝色", "image": "/static/catalog/cup/0.jpg"}]),
        ),
    )

    class DetailEditor:
        def __init__(self):
            self.calls = []

        def edit(self, data, prompt, size="1024x1024"):
            self.calls.append((prompt, size))
            made = Image.new("RGB", (32, 48), (255, 255, 255))
            buf = io.BytesIO()
            made.save(buf, format="JPEG")
            return buf.getvalue()

    editor = DetailEditor()
    count = generate_story(
        conn,
        tmp_path,
        "cup",
        "en",
        editor,
        ocr=lambda path: "加厚乳胶 38cm 厨房使用 注意清洗",
    )
    assert count == len(editor.calls)
    assert "product is the subject" in editor.calls[0][0]
    assert "Do not add any text" in editor.calls[0][0]
    assert "Any words on the image" not in editor.calls[0][0]
    assert "what it is for" in editor.calls[1][0]
    assert "image 3 of 3" in editor.calls[2][0]
    assert all(prompt != HERO_PROMPT for prompt, _size in editor.calls)
    assert any(size == "1024x1536" for _prompt, size in editor.calls)
    saved = (folder / "en" / "story" / "facts.txt").read_text(encoding="utf-8")
    assert "红色+蓝色" in saved
    detail_prompts = [prompt for prompt, size in editor.calls if size == "1024x1536"]
    assert detail_prompts
    assert all("红色+蓝色" not in prompt for prompt in detail_prompts)
    assert any("one large number" in prompt for prompt in detail_prompts)
    assert any("close-up" in prompt for prompt in detail_prompts)
    assert any("brand names" in prompt for prompt, _size in editor.calls)
    assert any("photorealistic adult" in prompt for prompt, _size in editor.calls)
    assert (folder / "en" / "main" / "1.jpg").is_file()
    assert (folder / "en" / "main" / "3.jpg").is_file()
    assert not (folder / "en" / "main" / "4.jpg").exists()
    (folder / "en" / "main" / "4.jpg").write_bytes(b"white-fourth")
    assert (folder / "en" / "story" / "1.jpg").is_file()
    assert (folder / "en" / "story" / "facts.txt").read_text(encoding="utf-8")
    again = generate_story(
        conn,
        tmp_path,
        "cup",
        "en",
        editor,
        ocr=lambda path: "加厚乳胶 38cm",
    )
    assert again >= 1
    assert (folder / "en" / "main" / "4.jpg").read_bytes() == b"white-fourth"
    assert not (folder / "en" / "story" / ("%s.jpg" % (again + 1))).exists()


def test_story_keeps_landed_frames_and_draws_only_the_gaps(tmp_path):
    folder = tmp_path / "static" / "catalog" / "cup"
    folder.mkdir(parents=True)
    image = Image.new("RGB", (80, 80), (20, 40, 60))
    out = io.BytesIO()
    image.save(out, format="JPEG")
    (folder / "0.jpg").write_bytes(out.getvalue())
    conn = connect(str(tmp_path / "shop.sqlite"))
    migrate(conn)
    conn.execute(
        """
        insert into products
            (sku, category, price_cents, stock, names, bullets, description, specs, image_url, listing, offers)
        values ('cup', 'kitchen', 500, 1, '{}', '{}', '{}', '{}', '/static/catalog/cup/0.jpg', '{}', '[]')
        """
    )
    kept = folder / "en" / "main"
    kept.mkdir(parents=True)
    (kept / "1.jpg").write_bytes(b"keep-this-frame")
    (folder / "en" / "story").mkdir(parents=True)
    (folder / "en" / "story" / "2.jpg").write_bytes(b"keep-story")

    class Editor:
        def __init__(self):
            self.calls = 0

        def edit(self, data, prompt, size="1024x1024"):
            self.calls += 1
            made = Image.new("RGB", (32, 32), (255, 255, 255))
            buf = io.BytesIO()
            made.save(buf, format="JPEG")
            return buf.getvalue()

    editor = Editor()
    generate_story(conn, tmp_path, "cup", "en", editor, ocr=lambda path: "", only_missing=True, workers=1)
    assert editor.calls == 6
    assert (kept / "1.jpg").read_bytes() == b"keep-this-frame"
    assert (folder / "en" / "story" / "2.jpg").read_bytes() == b"keep-story"
    assert (kept / "2.jpg").is_file()
    assert (kept / "3.jpg").is_file()
    assert (folder / "en" / "story" / "5.jpg").is_file()
    assert missing_story_slots(tmp_path, "cup", "en") == []


def test_story_draws_mains_and_details_together(tmp_path):
    folder = tmp_path / "static" / "catalog" / "cup"
    folder.mkdir(parents=True)
    image = Image.new("RGB", (80, 80), (20, 40, 60))
    out = io.BytesIO()
    image.save(out, format="JPEG")
    (folder / "0.jpg").write_bytes(out.getvalue())
    conn = connect(str(tmp_path / "shop.sqlite"))
    migrate(conn)
    conn.execute(
        """
        insert into products
            (sku, category, price_cents, stock, names, bullets, description, specs, image_url, listing, offers)
        values ('cup', 'kitchen', 500, 1, ?, '{}', '{}', '{}', '/static/catalog/cup/0.jpg', ?, '[]')
        """,
        (
            json.dumps({"en": "Dish gloves"}),
            json.dumps({"detail_images": ["/static/catalog/cup/0.jpg"]}),
        ),
    )

    class DetailEditor:
        def __init__(self):
            self.calls = []
            self.lock = threading.Lock()

        def edit(self, data, prompt, size="1024x1024"):
            with self.lock:
                self.calls.append((prompt, size))
            made = Image.new("RGB", (32, 48), (255, 255, 255))
            buf = io.BytesIO()
            made.save(buf, format="JPEG")
            return buf.getvalue()

    editor = DetailEditor()
    count = generate_story(
        conn,
        tmp_path,
        "cup",
        "en",
        editor,
        ocr=lambda path: "加厚乳胶 38cm 厨房使用 注意清洗",
        workers=8,
    )
    assert count == len(editor.calls)
    assert all(prompt != HERO_PROMPT for prompt, _size in editor.calls)
    assert any(size == "1024x1536" for _prompt, size in editor.calls)
    assert (folder / "en" / "main" / "1.jpg").is_file()
    assert (folder / "en" / "main" / "3.jpg").is_file()
    assert not (folder / "en" / "main" / "5.jpg").exists()
    assert (folder / "en" / "story" / "1.jpg").is_file()


def test_commerce_image_follows_the_selected_language_and_original_shape(tmp_path):
    assert "Japanese" in commerce_prompt("ja")
    assert "English" in commerce_prompt("en")
    image = Image.new("RGB", (800, 3200), (20, 40, 60))
    out = io.BytesIO()
    image.save(out, format="JPEG")
    path = tmp_path / "d0.jpg"
    path.write_bytes(out.getvalue())

    class DetailEditor:
        def __init__(self):
            self.calls = []

        def edit(self, data, prompt, size="1024x1024"):
            self.calls.append((prompt, size))
            made = Image.new("RGB", (32, 128), (255, 255, 255))
            buf = io.BytesIO()
            made.save(buf, format="JPEG")
            return buf.getvalue()

    editor = DetailEditor()
    body = CommerceImageClient(editor).translate(path, "ja")
    assert body.startswith(b"\xff\xd8")
    assert editor.calls == [(commerce_prompt("ja"), "1024x4096")]
