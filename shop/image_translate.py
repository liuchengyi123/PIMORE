import json
import os
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import httpx

import re
import shutil
import subprocess
import tempfile

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def image_ocr_text(path):
    """Text from tesseract, or None when OCR cannot run."""
    path = Path(path)
    if not path.is_file():
        return None
    if shutil.which("tesseract") is None:
        return None
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return None
    tmp = None
    try:
        with Image.open(path) as raw:
            image = ImageOps.exif_transpose(raw).convert("L")
        longest = max(image.size)
        if longest > 1280:
            scale = 1280 / float(longest)
            image = image.resize(
                (max(1, int(image.size[0] * scale)), max(1, int(image.size[1] * scale))),
                Image.Resampling.BILINEAR,
            )
        image = ImageOps.autocontrast(image)
        fd, tmp = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        image.save(tmp, format="PNG")
        proc = None
        for lang in ("chi_sim+eng", "chi_sim"):
            proc = subprocess.run(
                [
                    "tesseract",
                    tmp,
                    "stdout",
                    "-l",
                    lang,
                    "--psm",
                    "6",
                    "-c",
                    "preserve_interword_spaces=1",
                ],
                capture_output=True,
                timeout=25,
                check=False,
            )
            if proc.returncode in (0, 1):
                break
        if proc is None or proc.returncode not in (0, 1):
            err = ((proc.stderr if proc else b"") or b"").decode("utf-8", "ignore").lower()
            if "error" in err or "failed" in err:
                return None
        return (proc.stdout or b"").decode("utf-8", "ignore").strip()
    except Exception:
        return None
    finally:
        if tmp:
            try:
                Path(tmp).unlink(missing_ok=True)
            except Exception:
                pass


def image_has_cjk(path):
    """True if OCR finds Chinese; False if OCR ran and found none; None if OCR unavailable.

    Uses system tesseract (chi_sim) when present. Fail-open (None) so missing OCR
    never blocks translation — only confirmed no-CJK images are skipped.
    """
    text = image_ocr_text(path)
    if text is None:
        return None
    return bool(_CJK_RE.search(text))



MODEL = "qwen-mt-image-2.0"
IMAGE_LANGS = {
    "en": "英语",
    "ja": "日语",
    "es": "西班牙语",
    "fr": "法语",
    "pt": "葡萄牙语",
}


class ImageTranslateError(Exception):
    pass


class ImageAuthError(ImageTranslateError):
    pass


def stamp_missing_uploads(conn, catalog, today):
    rows = conn.execute("select sku, uploaded_at from products").fetchall()
    for row in rows:
        if str(row["uploaded_at"] or "").strip():
            continue
        folder = Path(catalog) / row["sku"]
        if folder.is_dir():
            day = datetime.fromtimestamp(folder.stat().st_mtime).date().isoformat()
        else:
            day = today
        conn.execute(
            "update products set uploaded_at = ? where sku = ? and uploaded_at = ''",
            (day, row["sku"]),
        )


def catalog_file(url, root):
    text = str(url or "")
    if not text.startswith("/static/catalog/"):
        return None
    relative = Path(text[len("/static/"):])
    if len(relative.parts) != 3 or relative.parts[0] != "catalog":
        return None
    path = Path(root) / "static" / relative
    if not path.is_file():
        return None
    return path


def language_file(path, lang):
    return Path(path).parent / lang / Path(path).name


def storefront_image(url, lang, root):
    path = catalog_file(url, root)
    if path is None:
        return url
    order = [lang] if lang == "en" else [lang, "en"]
    for code in order:
        if code not in IMAGE_LANGS:
            continue
        candidate = language_file(path, code)
        if candidate.is_file():
            return f"/static/catalog/{path.parent.name}/{code}/{path.name}"
    return url


def product_image_urls(row):
    found = []

    def add(url):
        if url and url not in found:
            found.append(url)

    add(row["image_url"] if "image_url" in row.keys() else "")
    try:
        listing = json.loads(row["listing"] or "{}")
    except json.JSONDecodeError:
        listing = {}
    if isinstance(listing, dict):
        for key in ("gallery", "detail_images"):
            for url in listing.get(key) or []:
                add(url)
    try:
        offers = json.loads(row["offers"] or "[]")
    except json.JSONDecodeError:
        offers = []
    for offer in offers if isinstance(offers, list) else []:
        if isinstance(offer, dict):
            add(offer.get("image") or "")
    return found


def resume_range(rows, start, end):
    start = str(start or "")
    end = str(end or "")
    if start and end and start <= end:
        return start, end
    days = sorted({str(row["uploaded_at"] or "") for row in rows if str(row["uploaded_at"] or "")})
    if not days:
        raise ImageTranslateError("没有可继续的上传日期。")
    return days[0], days[-1]


def pending_images(rows, root, lang, start="", end="", sku=""):
    """Every image that does not yet have this language file. Upload dates are not a filter."""
    if lang not in IMAGE_LANGS:
        raise ImageTranslateError("一次只能选一种语言。德语这档模型译不了。")
    wanted = str(sku or "").strip()
    tasks = []
    for row in rows:
        if wanted and str(row["sku"] or "") != wanted:
            continue
        for url in product_image_urls(row):
            path = catalog_file(url, root)
            if path is None or language_file(path, lang).is_file():
                continue
            tasks.append((row["sku"], path))
    return tasks


class _ImageGate:
    """At most 60 sync calls at once, and a new one starts about once a second."""

    def __init__(self, slots=60, interval=1.05, clock=None, sleep=None):
        self._slots = threading.Semaphore(slots)
        self._interval = interval
        self._clock = clock or time.monotonic
        self._sleep = sleep or time.sleep
        self._lock = threading.Lock()
        self._next = 0.0

    def acquire(self):
        self._slots.acquire()
        with self._lock:
            now = self._clock()
            delay = self._next - now
            self._next = max(self._next, now) + self._interval
        if delay > 0:
            self._sleep(delay)

    def release(self):
        self._slots.release()


_image_gate = _ImageGate()


class QwenImageClient:
    def __init__(self, api_key, workspace=""):
        self.api_key = (api_key or "").strip()
        self.workspace = (workspace or "").strip()
        if not self.api_key:
            raise ImageAuthError("还没有百炼密钥。")

    def _root(self):
        if self.workspace:
            return f"https://{self.workspace}.cn-beijing.maas.aliyuncs.com/api/v1"
        return "https://dashscope.aliyuncs.com/api/v1"

    def translate(self, path, lang):
        if lang not in IMAGE_LANGS:
            raise ImageTranslateError("一次只能选一种语言。德语这档模型译不了。")
        path = Path(path)
        data = path.read_bytes()
        suffix = path.suffix.lower() if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"} else ".jpg"
        name = f"{path.parent.name}-{uuid.uuid4().hex[:8]}{suffix}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        last = None
        with httpx.Client(timeout=httpx.Timeout(120.0, connect=10.0)) as http:
            policy = self._policy(http, headers)
            oss_url = self._upload(http, policy, name, data)
            for attempt in range(3):
                try:
                    _image_gate.acquire()
                    try:
                        result_url = self._submit_sync(http, headers, oss_url, lang)
                    finally:
                        _image_gate.release()
                    if not result_url:
                        return data
                    downloaded = http.get(result_url, follow_redirects=True)
                    downloaded.raise_for_status()
                    return downloaded.content
                except ImageAuthError:
                    raise
                except ImageTranslateError as exc:
                    last = exc
                    if "限流" not in str(exc) or attempt == 2:
                        raise
                    time.sleep(2 * (attempt + 1))
                except Exception as exc:
                    last = exc
                    name_of = type(exc).__name__
                    if not any(token in name_of for token in ("Connect", "Timeout", "Proxy")) or attempt == 2:
                        raise
                    time.sleep(2 * (attempt + 1))
        raise last

    def _policy(self, http, headers):
        response = http.get(
            "https://dashscope.aliyuncs.com/api/v1/uploads",
            headers={**headers, "Content-Type": "application/json"},
            params={"action": "getPolicy", "model": MODEL},
        )
        self._raise_for_status(response)
        return response.json()["data"]

    def _upload(self, http, policy, name, data):
        key = f"{policy['upload_dir']}/{name}"
        response = http.post(
            policy["upload_host"],
            files=[
                ("OSSAccessKeyId", (None, policy["oss_access_key_id"])),
                ("Signature", (None, policy["signature"])),
                ("policy", (None, policy["policy"])),
                ("x-oss-object-acl", (None, policy["x_oss_object_acl"])),
                ("x-oss-forbid-overwrite", (None, policy["x_oss_forbid_overwrite"])),
                ("key", (None, key)),
                ("success_action_status", (None, "200")),
                ("file", (name, data)),
            ],
        )
        if response.status_code != 200:
            raise ImageTranslateError("原图没有传上去。")
        return f"oss://{key}"

    def _submit_sync(self, http, headers, oss_url, lang):
        response = http.post(
            f"{self._root()}/services/aigc/image2image/image-synthesis",
            headers={**headers, "Content-Type": "application/json", "X-DashScope-OssResourceResolve": "enable"},
            json={
                "model": MODEL,
                "input": {
                    "image_url": oss_url,
                    "source_lang": "zh",
                    "target_lang": lang,
                    "ext": {"config": {"imageSegment": True}},
                },
            },
        )
        self._raise_for_status(response)
        output = (response.json() or {}).get("output") or {}
        if output.get("image_url"):
            return output["image_url"]
        task_id = output.get("task_id") or ""
        if task_id:
            return self._wait(http, headers, task_id)
        raise ImageTranslateError("这一张没有译成。")

    def _wait(self, http, headers, task_id):
        for attempt in range(40):
            if attempt:
                time.sleep(1)
            try:
                response = http.get(f"{self._root()}/tasks/{task_id}", headers=headers)
            except Exception as exc:
                name = type(exc).__name__
                if not any(token in name for token in ("Connect", "Timeout", "Proxy")) or attempt > 30:
                    raise ImageTranslateError("这一张等得太久。") from exc
                continue
            if response.status_code == 429:
                continue
            self._raise_for_status(response)
            output = response.json().get("output") or {}
            status = output.get("task_status") or ""
            if status == "SUCCEEDED":
                return output.get("image_url") or ""
            if status in {"FAILED", "CANCELED", "UNKNOWN"}:
                raise ImageTranslateError("这一张没有译成。")
        raise ImageTranslateError("这一张等得太久。")

    def _raise_for_status(self, response):
        if response.status_code in {401, 403}:
            raise ImageAuthError("百炼密钥无效，或业务空间不对。")
        if response.status_code == 429:
            raise ImageTranslateError("接口限流")
        if response.status_code >= 400:
            code = ""
            try:
                code = response.json().get("code") or ""
            except Exception:
                code = ""
            if code in {"InvalidApiKey", "InvalidApiKey.Signature"}:
                raise ImageAuthError("百炼密钥无效，或业务空间不对。")
            raise ImageTranslateError("翻译接口没有完成。")
