import base64
import io
import json
import queue
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont, ImageOps

EDGE = 800
MARGIN_RATIO = 0.04
LANGS = ("en", "ja", "es", "fr", "pt", "de")

COMMERCE_LANGS = {
    "en": "English",
    "ja": "Japanese",
    "es": "Spanish",
    "fr": "French",
    "pt": "Brazilian Portuguese",
}


def commerce_prompt(lang):
    name = COMMERCE_LANGS.get(str(lang or "").strip(), "English")
    return (
        "The reference is only a source of facts. Do not keep its layout, crop, background, "
        "typography, or the positions of the photos. "
        "Design a new Western e-commerce detail image from scratch. "
        "Put the product in a new arrangement and write a new headline plus short lines. "
        "Translate every Chinese description into %s. The finished image must contain only %s text. "
        "Keep the same product: shape, parts, colors, and materials. "
        "Keep numbers, units, and measurements exactly as shown. "
        "Do not add features, awards, prices, or claims that are not in the reference. "
        "Do not leave any Chinese characters."
    ) % (name, name)


DETAIL_PROMPT = commerce_prompt("en")

STORY_SIZE = "1024x1536"
MAIN_SIZE = "1024x1024"
MAIN_ROLES = (
    (1, "Placed", "Show the product on display in a real Western home, placed where this kind of product is used. The product is the subject. One photograph only. No person. No words of any kind. Do not draw a grid of options or color chips."),
    (2, "In use", "Show the product being used in a Western home, so a shopper can tell what it is for at a glance. Generate a photorealistic adult when a person is needed. The person is generic, in Western clothing, not a celebrity and not a real identifiable person. One short headline is enough."),
    (3, "Fact", "One clean product photograph with one measurement or material from the facts. Copy numbers and units exactly. If the facts have no number, show the product with no invented figure. At most a short callout, not a specification table."),
)
STORY_ROLES = (
    (1, "Hero", "One photograph of the product being used in a Western home, with one short headline. No second photo, no inset circle, no row of products, no specification table."),
    (2, "Use", "A Western model using the product in a Western home. The person is in the frame, holding and using it. Generate a photorealistic adult. The person is generic, in Western clothing, not a celebrity and not a real identifiable person. If the facts describe a set, the set stays together. No specification numbers, no inset circle."),
    (3, "Specs", "Show the whole product on a plain light background with one large number copied exactly from the facts, plus at most two more short lines: one material and one count if they are written. If the facts describe a set, show the whole set, not one piece. No person, no room scene, no product-name headline. Do not invent a number."),
    (4, "Construction", "Fill the frame with a close-up of one piece from the product, so the material and the make are visible. If it is a set, this is one piece of that set, not a different product. No person, no headline."),
    (5, "Second detail", "A close-up of a different piece from the construction image, another part a shopper would inspect. If it is a set, this is another piece of that set. No person, no specification table."),
)


def story_fact_sheet(name, specs, detail_text, labels):
    """Notes for the whole set. Option labels are copied, not split on +."""
    lines = []
    if str(name or "").strip():
        lines.append("Product: %s" % str(name).strip())
    if str(specs or "").strip():
        lines.append("Specs: %s" % str(specs).strip())
    notes = str(detail_text or "").strip()
    if notes:
        lines.append("Text read from the detail images:\n%s" % notes[:4000])
    kept = [str(label).strip() for label in labels if str(label or "").strip()]
    if kept:
        lines.append("Option labels, copied as written: %s" % " | ".join(kept[:40]))
        if len(kept) > 40:
            lines.append("There are %s option labels. The rest are more of the same kind." % len(kept))
        lines.append(
            "A plus sign, slash, or the word and inside a label is not two products. "
            "Look at the reference photo. If both colors are on one object, it is one product. "
            "If the photo shows a single color, that label is one option."
        )
    lines.append("Do not add features, awards, prices, or claims that are not written above.")
    return "\n".join(lines)


def story_panels(facts):
    """Five detail photos. Size and specs share one frame. Care is not used."""
    del facts
    return [
        {"index": number, "title": title, "task": task}
        for number, title, task in STORY_ROLES
    ]


def _is_set(text):
    raw = str(text or "")
    folded = raw.lower()
    return any(word in raw or word in folded for word in ("set", "piece", "pcs", "kit", "套装", "件套"))


def _set_lines(notes):
    kept = []
    for line in str(notes or "").splitlines():
        if _is_set(line):
            kept.append(line.strip())
    return "\n".join(kept)


def _matching_lines(notes, words, limit=3):
    kept = []
    for line in str(notes or "").splitlines():
        line = line.strip()
        if not line:
            continue
        folded = line.lower()
        if any(word in line or word in folded for word in words):
            kept.append(line)
        if len(kept) >= limit:
            break
    return "\n".join(kept)


def story_panel_facts(panel, name, specs, detail_text):
    """One short fact for this photo. The old detail page is not pasted in."""
    title = panel["title"]
    product = str(name or "").strip()
    measures = str(specs or "").strip()
    notes = str(detail_text or "").strip()
    bundle = _set_lines(notes)
    if title == "Measurement":
        body = "\n".join(part for part in (measures or product, bundle) if part)
    elif title == "Construction":
        body = "\n".join(
            part for part in (_matching_lines(notes, ("material", "latex", "steel", "cotton", "材质", "乳胶", "不锈钢", "棉", "塑料", "硅胶")) or measures or product, bundle)
            if part
        )
    elif title == "Specs":
        body = "\n".join(part for part in (product, measures, bundle) if part)
    elif title == "Care":
        body = "\n".join(
            part for part in (_matching_lines(notes, ("wash", "clean", "caution", "注意", "清洗", "勿", "不可", "保养")) or product, bundle)
            if part
        )
    elif title == "Use":
        body = "\n".join(
            part for part in (product, _matching_lines(notes, ("kitchen", "bath", "room", "wear", "use", "厨房", "卫生间", "浴室", "使用", "家用")), bundle)
            if part
        )
    else:
        body = "\n".join(part for part in (product, bundle) if part)
    return body[:400]


def _market_look(square):
    """Shared look for the three square mains and the five portrait details."""
    kind = "square main photo" if square else "portrait detail photo"
    return (
        "Make a photorealistic %s for a Western European or North American online shop. "
        "Natural daylight, a real home or a plain studio, simple framing, the product easy to recognize. "
        "Do not copy a Chinese marketplace poster. "
        "No red stamps, price tags, QR codes, cartoon icons, badge walls, dense caption blocks, "
        "multi-panel collages, or before-and-after grids. "
    ) % kind


def _reference_sentence(title):
    if title in ("Construction", "Second detail", "Detail"):
        return (
            "The reference photo is the real product. "
            "This frame shows one piece that is visible in that photo. Do not invent a different tool. "
        )
    if title == "Placed":
        return (
            "The reference photo is the real product. Keep every piece, the case, and the colors that are visible in it. "
            "Do not drop a piece that is in the photo, and do not add a piece that is not. "
            "You may change the background and the crop. "
        )
    return (
        "The reference photo is the real product. Keep every piece, the case, and the colors that are visible in it. "
        "Do not drop a piece that is in the photo, and do not add a piece that is not. "
        "You may change the background, the crop, and the text. "
    )


def _set_sentence(title, facts):
    if not _is_set(facts):
        return ""
    if title in ("Construction", "Second detail", "Detail"):
        return " This frame is one piece of the set, not a different product."
    return " Show the whole set together, including the case if one is named. Do not replace the set with a single tool."


def story_prompt(lang, facts, panel, previous):
    del previous
    name = COMMERCE_LANGS.get(str(lang or "").strip(), "English")
    fact_line = ""
    if str(facts or "").strip():
        fact_line = "Use only these facts: %s. " % " ".join(str(facts).split())
    return (
        "The attached photo is the product. "
        "%s"
        "Take a new portrait detail photo of that same product for a Western product page. "
        "This photo is the %s photo. %s "
        "%s%s "
        "%s"
        "Any words on the image are short and in %s. "
        "Translate the facts into %s. Copy numbers and units exactly. Do not invent a number. "
        "No brand names, prices, rankings, or claims that are not in the attached photo. "
        "No Chinese characters."
    ) % (
        _market_look(False),
        panel["title"],
        panel["task"],
        _reference_sentence(panel["title"]),
        _set_sentence(panel["title"], facts),
        fact_line,
        name,
        name,
    )

# Sizes the image API accepts. Each pair is width x height.
DETAIL_SIZES = (
    (1024, 1024), (2048, 2048), (3840, 3840),
    (1152, 896), (2048, 1536), (3840, 2880),
    (896, 1152), (1536, 2048), (2880, 3840),
    (1536, 864), (2048, 1152), (3840, 2160),
    (864, 1536), (1152, 2048), (2160, 3840),
    (1536, 1024), (2048, 1360), (3840, 2560),
    (1024, 1536), (1360, 2048), (2560, 3840),
    (1280, 1024), (2560, 2048), (3840, 3072),
    (1024, 1280), (2048, 2560), (3072, 3840),
    (1792, 768), (2048, 880), (3840, 1648),
    (512, 2048), (1024, 4096),
    (2048, 512), (4096, 1024),
    (1440, 1024), (2048, 1456), (3840, 2720),
    (1024, 1440), (1456, 2048), (2720, 3840),
)


def fit_size(width, height):
    """Closest supported canvas to the original image."""
    width = int(width or 0)
    height = int(height or 0)
    if width <= 0 or height <= 0:
        return "1024x1024"
    ratio = width / float(height)
    longest = max(width, height)
    best = DETAIL_SIZES[0]
    best_score = None
    for candidate in DETAIL_SIZES:
        aspect = abs((candidate[0] / float(candidate[1])) - ratio)
        scale = abs(max(candidate) - longest) / float(longest)
        score = aspect * 8 + scale
        if best_score is None or score < best_score:
            best = candidate
            best_score = score
    return "%sx%s" % best


HERO_PROMPT = (
    "Use the reference photo only to identify this exact product. "
    "Take a new square studio packshot of that same product on a seamless white sweep (#FFFFFF). "
    "Keep the same object: same shape, parts, hole count, color, logos, printed marks, and material. "
    "Keep it centered, occupying about 80% of the frame, with a similar margin on every side. "
    "Do not keep the original crop, camera distance, or background. "
    "Relight it with a soft overhead studio light. "
    "Leave a soft contact shadow directly under the product so it sits on the white surface. "
    "Glass and metal keep soft highlights from that light. "
    "No hands, extra props, room, or colored backdrop. "
    "Do not add any text, letters, numbers, watermark, caption, label, or border."
)

COLOR_WORDS = (
    "red", "green", "blue", "black", "white", "pink", "gray", "grey", "brown",
    "yellow", "orange", "purple", "violet", "gold", "silver", "beige", "navy",
    "khaki", "camouflage", "camo",
    "红", "绿", "蓝", "黑", "白", "粉", "灰", "棕", "咖", "黄", "橙", "紫", "金", "银", "青", "卡其", "迷彩",
)


class GenError(Exception):
    pass


def sku_prompt(label):
    """Shared white studio packshot for every language (no on-image text)."""
    return (
        "Use this reference photo of the color variant only to identify this exact product. "
        "Take a new square studio packshot of this same product on a seamless white sweep (#FFFFFF). "
        f"The product color is: {label}. "
        "Keep the same object: same shape, parts, hole count, color, logos, printed marks, and material. "
        "Keep it centered, occupying about 80% of the frame, with a similar margin on every side. "
        "Do not keep the original crop, camera distance, or background. "
        "Relight it with a soft overhead studio light. "
        "Leave a soft contact shadow directly under the product so it sits on the white surface. "
        "Glass and metal keep soft highlights from that light. "
        "No hands, extra props, room, or colored backdrop. "
        "Do not add any text, letters, numbers, watermark, caption, label, or border. "
        "Do not turn it into a different product."
    )


def _color_word(label):
    text = str(label or "")
    for word in COLOR_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", text, re.I) or (not word.isascii() and word in text):
            return True
    return False


def _is_quantity(label):
    text = str(label or "")
    if re.search(r"\d", text):
        return True
    return re.search(r"个装|只装|件装|套装|件套|pack|pcs|pieces|piece|\bset\b", text, re.I) is not None


def _label_parts(label):
    return [part.strip() for part in re.split(r"[+＋/＆&、]", str(label or "")) if part.strip()]


def _color_signature(label):
    text = str(label or "")
    found = []
    for word in COLOR_WORDS:
        matched = re.search(rf"\b{re.escape(word)}\b", text, re.I) or (not word.isascii() and word in text)
        if matched:
            found.append(word.lower())
    return tuple(found)


def skip_reason(label):
    text = str(label or "").strip()
    if not text:
        return "没有规格名"
    if _is_quantity(text):
        return "个数装或件套，不出图"
    parts = _label_parts(text)
    if len(parts) >= 2:
        signatures = [_color_signature(part) for part in parts]
        if not all(signatures):
            return "不是两种颜色的组合，不出图"
        if len(set(signatures)) < 2:
            return "同一种颜色写了两遍，不出图"
        return ""
    if not _color_word(text):
        return "不是颜色规格，不出图"
    return ""


def redraws_product(label):
    return skip_reason(label) == ""


def is_sku_spec_image(image):
    """True for dedicated SKU/规格图 files like c0.jpg / s1.png (not main gallery)."""
    name = Path(str(image or "").split("?", 1)[0]).name.lower()
    return re.match(r"^[cs]\d+\.(jpg|jpeg|png|webp)$", name) is not None


def shot_task_id(product_sku, image):
    key = _jpg_url(image) or str(image or "").strip()
    return "%s::%s" % (product_sku, key)


def offer_text(offer):
    if not isinstance(offer, dict):
        return ""
    for key in ("source_label", "label"):
        value = offer.get(key) or ""
        if isinstance(value, dict):
            text = str(value.get("en") or value.get("zh") or "").strip()
            if text:
                return text
            continue
        text = str(value).strip()
        if text.startswith("{") and "en" in text:
            try:
                data = json.loads(text.replace("'", '"'))
            except json.JSONDecodeError:
                data = None
            if isinstance(data, dict):
                picked = str(data.get("en") or data.get("zh") or "").strip()
                if picked:
                    return picked
        if text:
            return text
    return ""


def _gallery(raw):
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    return [item for item in (data.get("gallery") or []) if isinstance(item, str) and item.startswith("/static/")]


def source_url(row):
    image = str(row["image_url"] or "").strip()
    if image.startswith("/static/catalog/"):
        return image
    gallery = _gallery(row["listing"] if "listing" in row.keys() else "")
    return gallery[0] if gallery else ""


def pending_rows(rows):
    found = []
    for row in rows:
        if str(row["gen_at"] or "").strip():
            continue
        if source_url(row):
            found.append(row)
    return found


def _font(size):
    for path in (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def to_square(data, edge=EDGE):
    image = Image.open(io.BytesIO(data))
    image = ImageOps.exif_transpose(image).convert("RGB")
    if image.size != (edge, edge):
        image = ImageOps.pad(image, (edge, edge), color=(255, 255, 255), centering=(0.5, 0.5))
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=90, subsampling=0)
    return out.getvalue()


def _lines(draw, text, max_width):
    size = max(36, round(EDGE / 16))
    floor = max(28, round(EDGE / 22))
    while size >= floor:
        font = _font(size)
        words = text.split()
        if not words:
            return font, []
        rows = []
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if draw.textlength(trial, font=font) <= max_width:
                current = trial
            else:
                rows.append(current)
                current = word
        rows.append(current)
        too_wide = any(draw.textlength(row, font=font) > max_width for row in rows)
        if not too_wide:
            if len(rows) > 2:
                rows = rows[:2]
                rows[1] = rows[1].rstrip(" .") + "…"
            return font, rows
        size -= 2
    font = _font(floor)
    return font, [text[:18] + "…"]


def stamp_label(data, label):
    text = " ".join(str(label or "").split())
    image = Image.open(io.BytesIO(to_square(data))).convert("RGB")
    if not text:
        out = io.BytesIO()
        image.save(out, format="JPEG", quality=90, subsampling=0)
        return out.getvalue()
    draw = ImageDraw.Draw(image)
    margin = round(EDGE * MARGIN_RATIO)
    font, rows = _lines(draw, text, int(EDGE * 0.55))
    if not rows:
        out = io.BytesIO()
        image.save(out, format="JPEG", quality=90, subsampling=0)
        return out.getvalue()
    line_gap = 6
    heights = []
    widths = []
    for row in rows:
        box = draw.textbbox((0, 0), row, font=font)
        widths.append(box[2] - box[0])
        heights.append(box[3] - box[1])
    block_w = max(widths)
    block_h = sum(heights) + line_gap * (len(rows) - 1)
    right = EDGE - margin
    bottom = EDGE - margin
    pad = 8
    draw.rectangle(
        (right - block_w - pad * 2, bottom - block_h - pad, right, bottom),
        fill=(255, 255, 255),
    )
    y = bottom - block_h - pad // 2
    for row, width, height in zip(rows, widths, heights):
        draw.text((right - pad - width, y), row, fill=(28, 28, 28), font=font)
        y += height + line_gap
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=90, subsampling=0)
    return out.getvalue()


def catalog_path(url, root):
    text = str(url or "")
    if not text.startswith("/static/catalog/"):
        return None
    path = Path(root) / "static" / text[len("/static/"):]
    if ".." in path.parts:
        return None
    return path


def _jpg_url(url):
    path = Path(str(url).split("?", 1)[0])
    return str(path.with_suffix(".jpg")).replace("\\", "/")


def _clear_copies(path):
    for lang in LANGS:
        sibling = path.parent / lang / path.name
        if sibling.is_file():
            sibling.unlink()
    for folder in ("card", "view"):
        cached = path.parent / folder / f"{path.stem}.jpg"
        if cached.is_file():
            cached.unlink()


class HttpEditor:
    def __init__(self, url, token=""):
        self.url = str(url or "").rstrip("/")
        self.token = str(token or "").strip()
        self.name = self.url

    def edit(self, data, prompt):
        headers = {}
        if self.token:
            headers["X-Gen-Token"] = self.token
        try:
            response = httpx.post(
                self.url + "/edit",
                json={
                    "prompt": prompt,
                    "width": EDGE,
                    "height": EDGE,
                    "image_b64": base64.b64encode(data).decode("ascii"),
                },
                headers=headers,
                timeout=httpx.Timeout(300.0, connect=10.0),
                trust_env=False,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GenError("显卡没有返回图片。") from exc
        body = response.content
        if not body.startswith(b"\xff\xd8") and not body.startswith(b"\x89PNG"):
            raise GenError("显卡返回的不是图片。")
        return body


DEFAULT_GEN_API_URL = "https://agent3.shyfai.cn"
DEFAULT_GEN_API_MODEL = "gpt-image-2"
DEFAULT_GEN_API_WORKERS = 4
MAX_GEN_API_WORKERS = 5000


def _api_base(url):
    base = str(url or DEFAULT_GEN_API_URL).strip().rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3].rstrip("/")
    return base or DEFAULT_GEN_API_URL


def _image_bytes_from_payload(payload):
    items = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items:
        raise GenError("生图接口没有返回图片。")
    item = items[0] if isinstance(items[0], dict) else {}
    b64 = str(item.get("b64_json") or "").strip()
    if b64:
        if "," in b64 and b64.lower().startswith("data:"):
            b64 = b64.split(",", 1)[1]
        try:
            body = base64.b64decode(b64)
        except Exception as exc:
            raise GenError("生图接口返回的 Base64 无效。") from exc
        if body.startswith(b"\xff\xd8") or body.startswith(b"\x89PNG") or body.startswith(b"RIFF"):
            return body
        raise GenError("生图接口返回的不是图片。")
    url = str(item.get("url") or "").strip()
    if not url:
        raise GenError("生图接口没有返回图片地址。")
    try:
        response = httpx.get(url, timeout=httpx.Timeout(120.0, connect=10.0), follow_redirects=True, trust_env=False)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise GenError("下载生成图失败。") from exc
    body = response.content
    if not body.startswith(b"\xff\xd8") and not body.startswith(b"\x89PNG") and not body.startswith(b"RIFF"):
        raise GenError("下载到的不是图片。")
    return body


def _wait_api_task(status_url, deadline):
    last = {}
    while time.monotonic() < deadline:
        time.sleep(3)
        try:
            response = httpx.get(status_url, timeout=httpx.Timeout(30.0, connect=10.0), follow_redirects=True, trust_env=False)
            if response.status_code in (429, 466, 477, 488, 502, 503, 504):
                time.sleep(5)
                continue
            response.raise_for_status()
            last = response.json()
        except (httpx.HTTPError, json.JSONDecodeError, ValueError):
            continue
        status = str(last.get("status") or "").lower()
        if status == "completed":
            return last
        if status in ("failed", "cancelled"):
            error = last.get("error")
            if isinstance(error, dict):
                message = str(error.get("message") or error.get("code") or status)
            else:
                message = str(error or status)
            raise GenError("生图失败：" + message)
    raise GenError("生图超时，可稍后再试或查任务状态。")


class ApiEditor:
    """OpenAI-compatible image edits via shyfai / magic.art."""

    def __init__(self, url, key, model="", name=""):
        self.url = _api_base(url)
        self.key = str(key or "").strip()
        self.model = str(model or DEFAULT_GEN_API_MODEL).strip() or DEFAULT_GEN_API_MODEL
        self.name = name or ("api:" + self.url)

    def edit(self, data, prompt, size="1024x1024"):
        if not self.key:
            raise GenError("先保存生图 API 密钥。")
        if not self.url:
            raise GenError("先保存生图 API 地址。")
        text = str(prompt or "").strip()
        if not text or not data:
            raise GenError("生图缺少原图或提示词。")
        endpoint = self.url + "/v1/images/edits"
        headers = {
            "Authorization": "Bearer " + self.key,
            "Idempotency-Key": str(uuid.uuid4()),
        }
        files = [("image[]", ("source.jpg", data, "image/jpeg"))]
        form = {
            "model": self.model,
            "prompt": text,
            "n": "1",
            "size": str(size or "1024x1024"),
            "output_format": "jpeg",
            "response_format": "url",
        }
        deadline = time.monotonic() + 420
        try:
            response = httpx.post(
                endpoint,
                data=form,
                files=files,
                headers=headers,
                timeout=httpx.Timeout(420.0, connect=15.0),
                trust_env=False,
            )
        except httpx.HTTPError as exc:
            raise GenError("生图接口连不上。") from exc
        if response.status_code == 202:
            try:
                accepted = response.json()
            except json.JSONDecodeError as exc:
                raise GenError("生图接口受理响应无效。") from exc
            status_url = str(accepted.get("status_url") or "").strip()
            request_id = str(accepted.get("request_id") or accepted.get("id") or "").strip()
            if not status_url:
                if not request_id:
                    raise GenError("生图接口没有返回任务 ID。")
                status_url = self.url + "/v1/images/tasks/" + request_id
            payload = _wait_api_task(status_url, deadline)
            return _image_bytes_from_payload(payload)
        if response.status_code >= 400:
            message = ""
            try:
                err = response.json().get("error")
                if isinstance(err, dict):
                    message = str(err.get("message") or err.get("code") or "")
                elif err:
                    message = str(err)
            except Exception:
                message = (response.text or "")[:180]
            if message:
                flat = " ".join(message.split())
                if (
                    "can't directly generate" in flat.lower()
                    or "无法在此对话中" in flat
                    or "生图指令" in flat
                    or "WritingBlock" in flat
                ):
                    flat = "接口没有返回图片，回的是一段文字。"
                elif len(flat) > 180:
                    flat = flat[:180]
                raise GenError("生图接口错误：" + flat)
            raise GenError("生图接口错误（HTTP %s）。" % response.status_code)
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            body = response.content
            if body.startswith(b"\xff\xd8") or body.startswith(b"\x89PNG"):
                return body
            raise GenError("生图接口返回无法解析。") from exc
        status = str(payload.get("status") or "").lower()
        if status in ("queued", "running"):
            status_url = str(payload.get("status_url") or "").strip()
            request_id = str(payload.get("request_id") or payload.get("id") or "").strip()
            if not status_url and request_id:
                status_url = self.url + "/v1/images/tasks/" + request_id
            if status_url:
                payload = _wait_api_task(status_url, deadline)
        elif status in ("failed", "cancelled"):
            raise GenError("生图失败：" + str(payload.get("error") or status))
        return _image_bytes_from_payload(payload)


_claim_lock = threading.Lock()


def enqueue(conn, skus, force=False):
    added = 0
    for sku in skus:
        row = conn.execute("select status from gen_tasks where sku = ?", (sku,)).fetchone()
        if row is None:
            conn.execute(
                "insert into gen_tasks (sku, status, worker, error) values (?, 'pending', '', '')",
                (sku,),
            )
            added += 1
        elif row["status"] == "failed" or (force and row["status"] != "pending"):
            conn.execute(
                "update gen_tasks set status = 'pending', worker = '', error = '' where sku = ?",
                (sku,),
            )
            added += 1
        elif force and row["status"] == "pending":
            added += 1
    return added


def claim_task(conn, worker):
    with _claim_lock:
        row = conn.execute(
            "select sku from gen_tasks where status = 'pending' order by rowid limit 1"
        ).fetchone()
        if row is None:
            return ""
        conn.execute(
            "update gen_tasks set status = 'running', worker = ?, touched = ? where sku = ? and status = 'pending'",
            (worker, time.time(), row["sku"]),
        )
        held = conn.execute(
            "select status, worker from gen_tasks where sku = ?",
            (row["sku"],),
        ).fetchone()
        if held and held["status"] == "running" and held["worker"] == worker:
            return row["sku"]
        return ""


def finish_task(conn, sku, ok, error=""):
    conn.execute(
        "update gen_tasks set status = ?, worker = '', error = ?, touched = ? where sku = ?",
        ("done" if ok else "failed", "" if ok else str(error or ""), time.time(), sku),
    )


def release_abandoned(conn):
    conn.execute(
        "update gen_tasks set status = 'failed', worker = '', error = ? where status = 'running'",
        ("上次中断了。再出这一件时，只补还没落库的图。",),
    )


def task_progress(conn):
    counts = {"pending": 0, "running": 0, "done": 0, "failed": 0}
    for row in conn.execute("select status, count(*) as n from gen_tasks group by status").fetchall():
        counts[row["status"]] = row["n"]
    cols = {row[1] for row in conn.execute("pragma table_info(gen_tasks)").fetchall()}
    order = "touched desc, rowid" if "touched" in cols else "rowid"
    touched_filter = "(touched > 0 and status in ('done', 'failed'))" if "touched" in cols else "status in ('done', 'failed')"
    current = conn.execute(
        f"select sku from gen_tasks where status = 'running' order by {order} limit 1"
    ).fetchone()
    latest = conn.execute(
        f"select error from gen_tasks where status = 'failed' and error != '' order by {order} desc limit 1"
    ).fetchone()
    shown = conn.execute(
        f"""
        select sku, status, error from gen_tasks
        where status = 'running'
           or {touched_filter}
        order by case status when 'running' then 0 else 1 end, {order} desc
        limit 20
        """
    ).fetchall()
    total = sum(counts.values())
    return {
        "running": bool(counts["pending"] or counts["running"]),
        "label": current["sku"] if current else "",
        "done": counts["done"] + counts["failed"],
        "total": total,
        "pending": counts["pending"],
        "active": counts["running"],
        "error": latest["error"] if latest else "",
        "items": [
            {"sku": row["sku"], "status": row["status"], "error": row["error"] or ""}
            for row in shown
        ],
        "result": {"done": counts["done"], "failed": counts["failed"]},
    }


def spread(items, editors, fn):
    if not editors:
        raise GenError("先配置生图 API，或连上显卡。")
    if not items:
        return []
    pending = queue.Queue()
    for item in items:
        pending.put(item)
    errors = []
    lock = threading.Lock()

    def work(editor):
        while True:
            try:
                item = pending.get_nowait()
            except queue.Empty:
                return
            try:
                fn(editor, item)
            except Exception as exc:
                with lock:
                    errors.append(exc)

    threads = [threading.Thread(target=work, args=(editor,), daemon=True) for editor in editors]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return errors


def _offers(raw):
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _read_source(row, root):
    url = source_url(row)
    path = catalog_path(url, root)
    if path is None or not path.is_file():
        raise GenError("这个商品没有原图，不能出图。")
    return url, path.read_bytes()


def _backup(path, backup_root, sku):
    if backup_root is None or not path.is_file():
        return
    dest = Path(backup_root) / sku / path.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        dest.write_bytes(path.read_bytes())


def _commit_image(path, data, backup_root, sku):
    if path is None:
        return
    _backup(path, backup_root, sku)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    _clear_copies(path)


def _uses_main_image(image, main_url):
    text = str(image or "").strip()
    if not text:
        return True
    return _jpg_url(text) == _jpg_url(main_url)


def has_pending_shot(row):
    return any(item["action"] == "generate" for item in plan_product(row))


def plan_queue(conn):
    rows = conn.execute(
        """
        select t.sku as sku, p.image_url, p.listing, p.offers, p.gen_at
        from gen_tasks t
        left join products p on p.sku = t.sku
        where t.status = 'pending'
        order by t.rowid
        """
    ).fetchall()
    items = []
    for row in rows:
        planned = plan_product(row)
        generate_rows = [item for item in planned if item["action"] == "generate"]
        skip_rows = [item for item in planned if item["action"] != "generate"]
        if generate_rows:
            note = "、".join(item["label"] for item in generate_rows)
        elif skip_rows:
            note = skip_rows[0]["reason"]
        else:
            note = "没有要出的图"
        if len(note) > 80:
            note = note[:80] + "…"
        items.append({
            "sku": row["sku"],
            "generate": len(generate_rows),
            "skip": len(skip_rows),
            "note": note,
        })
    calling = sum(1 for item in items if item["generate"])
    return {
        "pending": len(items),
        "calling": calling,
        "shots": sum(item["generate"] for item in items),
        "idle": len(items) - calling,
        "items": items,
    }


def plan_product(row):
    """Normal product gen plans only main #4 (白底棚拍). SKU packshots use sku_gen_*."""
    source = source_url(row)
    items = []
    if str(row["gen_at"] or "").strip():
        items.append({"label": "主图第4张", "action": "skip", "reason": "主图第4张已经落库"})
    elif not source:
        items.append({"label": "主图第4张", "action": "skip", "reason": "没有原图"})
    else:
        items.append({
            "label": "主图第4张",
            "action": "generate",
            "reason": "按原图出一张白底主图，写入 en/main/4.jpg",
        })
    return items


def _shot_key(offer, source_url_value):
    if offer.get("generated"):
        return ""
    image = str(offer.get("image") or "").strip()
    if _uses_main_image(image, source_url_value):
        return ""
    if not is_sku_spec_image(image):
        return ""
    return _jpg_url(image)


def _as_jpeg(data):
    if data.startswith(b"\xff\xd8"):
        return data
    image = Image.open(io.BytesIO(data))
    image = ImageOps.exif_transpose(image).convert("RGB")
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=90, subsampling=0)
    return out.getvalue()


def _image_size(data):
    image = Image.open(io.BytesIO(data))
    image = ImageOps.exif_transpose(image)
    return image.size


class CommerceImageClient:
    """Turn one catalog photo into a Western commerce image in the chosen language."""

    def __init__(self, editor):
        self.editor = editor

    def translate(self, path, lang):
        data = Path(path).read_bytes()
        width, height = _image_size(data)
        return _as_jpeg(self.editor.edit(data, commerce_prompt(lang), size=fit_size(width, height)))


def generate_details(conn, root, sku, editor, workers=1):
    """Western English detail images from the original detail photos. One file, one call."""
    from shop.image_translate import catalog_file, language_file

    row = conn.execute(
        "select sku, listing from products where sku = ?",
        (sku,),
    ).fetchone()
    if row is None:
        raise GenError("没有这个商品。")
    try:
        listing = json.loads(row["listing"] or "{}")
    except json.JSONDecodeError:
        listing = {}
    urls = []
    if isinstance(listing, dict):
        for url in listing.get("detail_images") or []:
            if url and url not in urls:
                urls.append(url)
    if not urls:
        raise GenError("这个商品没有详情图。")
    pending = []
    for url in urls:
        path = catalog_file(url, root)
        if path is None:
            continue
        if language_file(path, "en").is_file():
            continue
        pending.append(path)
    if not pending:
        raise GenError("这件详情已经出过英文图，不会再出。")
    errors = []
    lock = threading.Lock()

    def run(path):
        data = path.read_bytes()
        try:
            width, height = _image_size(data)
            shot = _as_jpeg(editor.edit(data, DETAIL_PROMPT, size=fit_size(width, height)))
        except GenError as exc:
            with lock:
                errors.append("%s：%s" % (path.name, str(exc)[:120]))
            return
        dest = language_file(path, "en")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(shot)

    width = max(1, min(MAX_GEN_API_WORKERS, int(workers or 1)))
    with ThreadPoolExecutor(max_workers=min(width, len(pending))) as pool:
        list(pool.map(run, pending))
    if errors:
        raise GenError("有详情没出成，已经落下的不会再出。再跑一次只补失败的。" + errors[0])
    return len(pending)


def generate_product(conn, root, sku, editor, backup_root=None, force=False, workers=1):
    """Only generate the 1 main packshot at slot 4 (en/main/4.jpg).

    SKU/规格白底图走 generate_sku_shots / sku_gen_tasks，不在这条链路里出。
    """
    del workers  # main path is one shot; workers kept for call-site compatibility
    row = conn.execute(
        "select sku, image_url, listing, offers, gen_at from products where sku = ?",
        (sku,),
    ).fetchone()
    if row is None:
        raise GenError("没有这个商品。")
    source_url_value = source_url(row)
    offers = [dict(offer) for offer in _offers(row["offers"])]
    gen_at = str(row["gen_at"] or "").strip()
    fourth = Path(root) / "static" / "catalog" / str(sku) / "en" / "main" / "4.jpg"
    if gen_at and fourth.is_file() and not force:
        raise GenError("这个商品已经出过主图第4张，不会再跑。")
    if not source_url_value and not force:
        raise GenError("这个商品没有原图，不能出图。")

    source_url_value, source = _read_source(row, root)
    hero = to_square(editor.edit(source, HERO_PROMPT))
    _commit_image(fourth, hero, backup_root, sku)
    hero_url = _jpg_url(source_url_value) or source_url_value
    for offer in offers:
        image = str(offer.get("image") or "").strip()
        if _uses_main_image(image, source_url_value):
            offer["image"] = hero_url
    gen_at = date.today().isoformat()
    conn.execute(
        "update products set image_url = ?, offers = ?, gen_at = ? where sku = ?",
        (
            hero_url,
            json.dumps(offers, ensure_ascii=False) if offers else (row["offers"] or "[]"),
            gen_at,
            sku,
        ),
    )
    return hero_url


def plan_sku_product(row, force=False, root=None):
    """Budget SKU packshots for one product.

    Eligible units are dedicated 规格图 files (c*/s* under catalog), not main image.
    Color/quantity label filters are NOT used — every real SKU shot is queued.
    Shared white studio shots; no language sidecars.
    """
    source = source_url(row)
    offers = _offers(row["offers"] if "offers" in row.keys() else "[]")
    items = []
    seen = set()
    for offer in offers:
        label = offer_text(offer) or "未命名规格"
        image = str(offer.get("image") or "").strip()
        if offer.get("generated") and not force:
            items.append({"label": label, "action": "skip", "reason": "规格白底图已经落库", "image": image})
            continue
        if _uses_main_image(image, source):
            items.append({"label": label, "action": "skip", "reason": "用的是主图，不另出规格图", "image": image})
            continue
        if not is_sku_spec_image(image):
            items.append({"label": label, "action": "skip", "reason": "不是 c*/s* 规格图文件", "image": image})
            continue
        key = _jpg_url(image)
        if not key:
            items.append({"label": label, "action": "skip", "reason": "没有规格原图", "image": image})
            continue
        if key in seen:
            items.append({"label": label, "action": "skip", "reason": "和上面同一张原图，只出一次", "image": image})
            continue
        seen.add(key)
        if root is not None:
            path = catalog_path(image, root)
            if path is None or not path.is_file():
                items.append({"label": label, "action": "skip", "reason": "规格原图文件不存在", "image": image})
                continue
        items.append({
            "label": label,
            "action": "generate",
            "reason": "参照原规格图出白底棚拍（各国语言共用）",
            "image": key,
        })
    return items


def has_pending_sku_shot(row, force=False, root=None):
    return any(item["action"] == "generate" for item in plan_sku_product(row, force=force, root=root))


def list_pending_sku_shot_units(conn, root=None, force=False, product_sku=None):
    """Yield dicts: id, product_sku, image, label — one per unique pending 规格图."""
    sql = (
        "select sku, image_url, listing, offers, gen_at, published from products "
        "where ifnull(published, 0) = 1"
    )
    args = []
    if product_sku:
        sql += " and sku = ?"
        args.append(product_sku)
    for row in conn.execute(sql, args).fetchall():
        for item in plan_sku_product(row, force=force, root=root):
            if item["action"] != "generate":
                continue
            image = item.get("image") or ""
            yield {
                "id": shot_task_id(row["sku"], image),
                "product_sku": row["sku"],
                "image": image,
                "label": item.get("label") or "",
            }


def count_pending_sku_shots(conn, root=None, force=False):
    return sum(1 for _ in list_pending_sku_shot_units(conn, root=root, force=force))


def enqueue_sku(conn, skus, force=False):
    """Back-compat: expand product SKUs into pending image-level shot tasks."""
    units = []
    wanted = {str(sku) for sku in skus}
    rows = (
        conn.execute(
            "select sku, image_url, listing, offers, gen_at, published from products where sku in (%s)"
            % ",".join("?" * len(wanted)),
            tuple(wanted),
        ).fetchall()
        if wanted
        else []
    )
    for row in rows:
        for item in plan_sku_product(row, force=force):
            if item["action"] != "generate":
                continue
            units.append({
                "id": shot_task_id(row["sku"], item["image"]),
                "product_sku": row["sku"],
                "image": item["image"],
                "label": item.get("label") or "",
            })
    # also re-queue failed shot tasks for these products
    return enqueue_sku_shots(conn, units, force=force)


def enqueue_sku_shots(conn, units, force=False):
    """Enqueue image-level SKU packshot tasks. Each unit is one 规格图."""
    added = 0
    for unit in units:
        task_id = unit.get("id") or shot_task_id(unit["product_sku"], unit["image"])
        product_sku = unit["product_sku"]
        image = unit["image"]
        row = conn.execute("select status from sku_gen_tasks where id = ?", (task_id,)).fetchone()
        if row is None:
            conn.execute(
                "insert into sku_gen_tasks (id, product_sku, image, status, worker, error) values (?, ?, ?, 'pending', '', '')",
                (task_id, product_sku, image),
            )
            added += 1
        elif row["status"] == "failed" or (force and row["status"] not in ("pending", "running")):
            conn.execute(
                "update sku_gen_tasks set status = 'pending', worker = '', error = '', product_sku = ?, image = ? where id = ?",
                (product_sku, image, task_id),
            )
            added += 1
        elif force and row["status"] == "pending":
            added += 1
    # Re-queue failed tasks globally when force=False was used by rest endpoint separately
    return added


def claim_sku_task(conn, worker):
    """Claim one pending 规格图 task. Returns dict or None."""
    with _claim_lock:
        row = conn.execute(
            "select id, product_sku, image from sku_gen_tasks where status = 'pending' order by rowid limit 1"
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            "update sku_gen_tasks set status = 'running', worker = ?, touched = ? where id = ? and status = 'pending'",
            (worker, time.time(), row["id"]),
        )
        held = conn.execute(
            "select status, worker from sku_gen_tasks where id = ?",
            (row["id"],),
        ).fetchone()
        if held and held["status"] == "running" and held["worker"] == worker:
            return {
                "id": row["id"],
                "product_sku": row["product_sku"],
                "image": row["image"],
            }
        return None


def finish_sku_task(conn, task_id, ok, error=""):
    conn.execute(
        "update sku_gen_tasks set status = ?, worker = '', error = ?, touched = ? where id = ?",
        ("done" if ok else "failed", "" if ok else str(error or ""), time.time(), task_id),
    )


def release_abandoned_sku(conn):
    conn.execute(
        "update sku_gen_tasks set status = 'failed', worker = '', error = ? where status = 'running'",
        ("上次中断了。再出规格图时，只补还没落库的。",),
    )


def sku_task_progress(conn):
    counts = {"pending": 0, "running": 0, "done": 0, "failed": 0}
    for row in conn.execute("select status, count(*) as n from sku_gen_tasks group by status").fetchall():
        counts[row["status"]] = row["n"]
    current = conn.execute(
        "select product_sku, image from sku_gen_tasks where status = 'running' order by touched desc, rowid limit 1"
    ).fetchone()
    latest = conn.execute(
        "select error from sku_gen_tasks where status = 'failed' and error != '' order by touched desc, rowid desc limit 1"
    ).fetchone()
    total = sum(counts.values())
    label = ""
    if current:
        name = Path(str(current["image"] or "")).name
        label = "%s %s" % (current["product_sku"], name)
    return {
        "running": bool(counts["pending"] or counts["running"]),
        "label": label,
        "done": counts["done"] + counts["failed"],
        "total": total,
        "pending": counts["pending"],
        "active": counts["running"],
        "error": latest["error"] if latest else "",
        "result": {
            "done": counts["done"],
            "failed": counts["failed"],
        },
    }


def plan_sku_queue(conn):
    rows = conn.execute(
        """
        select id, product_sku, image, status
        from sku_gen_tasks
        where status = 'pending'
        order by rowid
        """
    ).fetchall()
    items = []
    for row in rows:
        name = Path(str(row["image"] or "")).name
        items.append({
            "sku": row["product_sku"],
            "generate": 1,
            "skip": 0,
            "note": name,
            "image": row["image"],
            "id": row["id"],
        })
    return {
        "pending": len(items),
        "calling": len(items),
        "shots": len(items),
        "idle": 0,
        "items": items,
    }


def generate_sku_shots(conn, root, sku, editor, backup_root=None, force=False, workers=1):
    """SKU-only white studio packshots.

    调用规则：
    - 参照该规格原图重拍；白底居中、软光接触阴影、画面无任何文字。
    - 成功后 offer.generated=1，各国语言共用同一张，不入多语言译图队列。
    - 默认跳过已 generated=1；force=True 才重出。
    - 并发用传入的 workers（后台 gen_api_workers）。
    - 优先给已上架商品用；本函数本身不筛选 published。
    """
    row = conn.execute(
        "select sku, image_url, listing, offers, gen_at from products where sku = ?",
        (sku,),
    ).fetchone()
    if row is None:
        raise GenError("没有这个商品。")
    source_url_value = source_url(row)
    offers = [dict(offer) for offer in _offers(row["offers"])]
    hero_url = _jpg_url(source_url_value) if source_url_value else ""
    pending = []
    seen = set()
    for index, offer in enumerate(offers):
        if offer.get("generated") and not force:
            continue
        key = _shot_key(offer, source_url_value) if not force else None
        if force:
            image = str(offer.get("image") or "").strip()
            if _uses_main_image(image, source_url_value):
                continue
            if not is_sku_spec_image(image):
                continue
            key = _jpg_url(image)
            if not key:
                continue
        if not key or key in seen:
            continue
        seen.add(key)
        pending.append(index)
    if not pending:
        raise GenError("这个商品没有要出的规格图。")

    def persist():
        conn.execute(
            "update products set offers = ? where sku = ?",
            (json.dumps(offers, ensure_ascii=False), sku),
        )

    errors = []
    lock = threading.Lock()

    def run_shot(index):
        offer = offers[index]
        image = str(offer.get("image") or "").strip()
        key = _jpg_url(image)
        siblings = [
            item for item in offers
            if _jpg_url(str(item.get("image") or "")) == key
            and (force or not item.get("generated"))
        ]
        label = offer_text(offer)
        src_path = catalog_path(image, root)
        if src_path is None or not src_path.is_file():
            with lock:
                for item in siblings:
                    if hero_url:
                        item["image"] = hero_url
                    item.pop("gen_error", None)
                persist()
            return
        try:
            shot = to_square(editor.edit(src_path.read_bytes(), sku_prompt(label)))
            dest_url = _jpg_url(image)
            dest = catalog_path(dest_url, root)
            _commit_image(dest, shot, backup_root, sku)
        except GenError as exc:
            message = str(exc)[:180]
            with lock:
                for item in siblings:
                    item["gen_error"] = message
                errors.append(label or key)
                persist()
            return
        with lock:
            for item in siblings:
                item["image"] = dest_url
                item["generated"] = 1
                item.pop("gen_error", None)
            persist()

    width = max(1, min(MAX_GEN_API_WORKERS, int(workers or 1)))
    with ThreadPoolExecutor(max_workers=min(width, len(pending))) as pool:
        list(pool.map(run_shot, pending))
    if errors:
        raise GenError("有规格没出成，已经落库的不会再出。再跑一次只补失败的。")
    return len(pending)


_product_offer_locks = {}
_product_offer_locks_guard = threading.Lock()


def _product_lock(product_sku):
    with _product_offer_locks_guard:
        lock = _product_offer_locks.get(product_sku)
        if lock is None:
            lock = threading.Lock()
            _product_offer_locks[product_sku] = lock
        return lock


def generate_one_sku_shot(conn, root, product_sku, image, editor, backup_root=None, force=False):
    """Generate a single SKU/规格白底图 unit (one c*/s* file). Thread-safe per product."""
    product_sku = str(product_sku or "").strip()
    image_key = _jpg_url(image) or str(image or "").strip()
    if not product_sku or not image_key:
        raise GenError("缺少货号或规格图路径。")
    with _product_lock(product_sku):
        row = conn.execute(
            "select sku, image_url, listing, offers, gen_at from products where sku = ?",
            (product_sku,),
        ).fetchone()
        if row is None:
            raise GenError("没有这个商品。")
        source_url_value = source_url(row)
        offers = [dict(offer) for offer in _offers(row["offers"])]
        hero_url = _jpg_url(source_url_value) if source_url_value else ""
        siblings = []
        for offer in offers:
            key = _jpg_url(str(offer.get("image") or ""))
            if key != image_key:
                continue
            if offer.get("generated") and not force:
                continue
            if _uses_main_image(str(offer.get("image") or ""), source_url_value):
                continue
            if not is_sku_spec_image(str(offer.get("image") or "")):
                continue
            siblings.append(offer)
        if not siblings:
            raise GenError("没有要出的规格图")
        src_image = str(siblings[0].get("image") or image_key).strip()
        src_path = catalog_path(src_image, root)
        if src_path is None or not src_path.is_file():
            for item in siblings:
                if hero_url:
                    item["image"] = hero_url
                item.pop("gen_error", None)
            conn.execute(
                "update products set offers = ? where sku = ?",
                (json.dumps(offers, ensure_ascii=False), product_sku),
            )
            raise GenError("规格原图文件不存在")
        label = offer_text(siblings[0])
        try:
            shot = to_square(editor.edit(src_path.read_bytes(), sku_prompt(label)))
            dest_url = _jpg_url(src_image)
            dest = catalog_path(dest_url, root)
            _commit_image(dest, shot, backup_root, product_sku)
        except GenError as exc:
            message = str(exc)[:180]
            for item in siblings:
                item["gen_error"] = message
            conn.execute(
                "update products set offers = ? where sku = ?",
                (json.dumps(offers, ensure_ascii=False), product_sku),
            )
            raise
        for item in siblings:
            item["image"] = dest_url
            item["generated"] = 1
            item.pop("gen_error", None)
        conn.execute(
            "update products set offers = ? where sku = ?",
            (json.dumps(offers, ensure_ascii=False), product_sku),
        )
        return 1



COVER_MODES = {
    "1": (1,),
    "2": (2,),
    "4": (4,),
    "12": (1, 2),
    "124": (1, 2, 4),
    "24": (2, 4),
    "14": (1, 4),
}


def normalize_cover(value):
    text = str(value or "").strip()
    return text if text in COVER_MODES else "1"


def cover_slot(sku, mode):
    """Which generated main this product leads with. A mix is stable per SKU."""
    slots = COVER_MODES[normalize_cover(mode)]
    if len(slots) == 1:
        return slots[0]
    n = 2166136261
    for ch in str(sku or ""):
        n = (n ^ ord(ch)) * 16777619 & 0xFFFFFFFF
    return slots[n % len(slots)]


def _main_number(url):
    name = str(url or "").rsplit("/", 1)[-1].split(".", 1)[0]
    return int(name) if name.isdigit() else 0


def order_mains(urls, sku, mode):
    """Put the chosen main first. A missing slot falls through the mix, then the other files."""
    urls = [str(url) for url in (urls or []) if url]
    if not urls:
        return []
    slots = COVER_MODES[normalize_cover(mode)]
    chosen = cover_slot(sku, mode)
    prefer = (chosen,) + tuple(number for number in slots if number != chosen)
    by_slot = {}
    for url in urls:
        number = _main_number(url)
        if number in slots and number not in by_slot:
            by_slot[number] = url
    ordered = [by_slot[number] for number in prefer if number in by_slot]
    used = set(ordered)
    return ordered + [url for url in urls if url not in used]


def main_urls(sku, lang, root):
    """Five generated gallery images for this language, in order."""
    folder = Path(root) / "static" / "catalog" / str(sku) / str(lang) / "main"
    if not folder.is_dir():
        return []
    files = [path for path in folder.glob("*.jpg") if path.stem.isdigit()]
    files.sort(key=lambda path: int(path.stem))
    return [
        "/static/catalog/%s/%s/main/%s" % (sku, lang, path.name)
        for path in files
    ]


def main_prompt(lang, facts, role, previous):
    del previous
    if role[1] == "Packshot":
        return HERO_PROMPT
    if role[1] == "Placed":
        return (
            "The attached photo is the product. "
            "%s"
            "Take a new square main photo of that same product for a Western product page. "
            "This photo is image 1 of 3. %s "
            "%s%s "
            "Do not add any text, letters, numbers, watermark, caption, headline, label, or border."
        ) % (_market_look(True), role[2], _reference_sentence(role[1]), _set_sentence(role[1], facts))
    name = COMMERCE_LANGS.get(str(lang or "").strip(), "English")
    fact_line = ""
    if str(facts or "").strip():
        fact_line = "Use only these facts: %s. " % " ".join(str(facts).split())
    return (
        "The attached photo is the product. "
        "%s"
        "Take a new square main photo of that same product for a Western product page. "
        "This photo is image %s of 3. %s "
        "%s%s "
        "%s"
        "Any words on the image are short and in %s. "
        "Translate the facts into %s. Copy numbers and units exactly. Do not invent a number. "
        "No brand names, prices, rankings, or claims that are not in the attached photo. "
        "No Chinese characters."
    ) % (_market_look(True), role[0], role[2], _reference_sentence(role[1]), _set_sentence(role[1], facts), fact_line, name, name)


def story_urls(sku, lang, root):
    """Generated detail set for this language, in order. Empty when it has not been made."""
    folder = Path(root) / "static" / "catalog" / str(sku) / str(lang) / "story"
    if not folder.is_dir():
        return []
    files = [path for path in folder.glob("*.jpg") if path.stem.isdigit()]
    files.sort(key=lambda path: int(path.stem))
    return [
        "/static/catalog/%s/%s/story/%s" % (sku, lang, path.name)
        for path in files
    ]


def _json_text(raw, lang="en"):
    try:
        data = json.loads(raw or "")
    except json.JSONDecodeError:
        return ""
    if isinstance(data, dict):
        if data.get(lang):
            return str(data.get(lang) or "")
        if data.get("en"):
            return str(data.get("en") or "")
        parts = []
        for key, value in data.items():
            if isinstance(value, dict):
                value = value.get(lang) or value.get("en") or ""
            if str(value or "").strip():
                parts.append("%s: %s" % (key, value))
        return "\n".join(parts)
    return str(data or "")


def _tighten_facts(facts, complete):
    if complete is None:
        return facts
    prompt = (
        "Rewrite the notes below into a short fact list. Keep every number and unit exactly. "
        "Do not add claims. Do not split an option label because it contains +, /, or and. "
        "Reply with the fact list only.\n\n%s" % facts
    )
    try:
        try:
            text = complete(prompt, 800)
        except TypeError:
            text = complete(prompt)
    except Exception:
        return facts
    cleaned = str(text or "").strip()
    return cleaned or facts


def _edit_shot(editor, reference, prompt, size):
    try:
        return editor.edit(reference, prompt, size=size)
    except TypeError:
        return editor.edit(reference, prompt)


_UPSTREAM_TRIES = 3
_UPSTREAM_PAUSE = 2


def _chat_reply(exc):
    text = str(exc)
    folded = text.lower()
    return (
        ("无法在此" in text and "图片" in text)
        or "回的是一段文字" in text
        or "生图指令" in text
        or "英文提示词" in text
        or "can't directly generate" in folded
        or "writingblock" in folded
    )


def _upstream_drop(exc):
    return "upstream request failed" in str(exc).lower()


def story_slot_paths(root, sku, lang):
    """The eight frames: main 1–3, then story 1–5."""
    base = Path(root) / "static" / "catalog" / str(sku) / str(lang)
    paths = []
    for folder, count in (("main", 3), ("story", 5)):
        for index in range(1, count + 1):
            paths.append(base / folder / ("%s.jpg" % index))
    return paths


def missing_story_slots(root, sku, lang):
    return [path for path in story_slot_paths(root, sku, lang) if not path.is_file()]


def _write_jobs(editor, reference, jobs, on_progress, done, total, workers=1, replace=True):
    """jobs are (folder, index, prompt, size). One worker keeps that order."""
    folders = []
    for folder, _index, _prompt, _size in jobs:
        if folder not in folders:
            folders.append(folder)
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
    if replace:
        for folder, index, _prompt, _size in jobs:
            old = folder / ("%s.jpg" % index)
            if old.is_file():
                old.unlink()
    if not replace:
        jobs = [job for job in jobs if not (job[0] / ("%s.jpg" % job[1])).is_file()]
        total = done + len(jobs)
    if not jobs:
        return done
    width = max(1, min(int(workers or 1), len(jobs)))
    skipped = {"n": 0}
    dropped = {"n": 0}
    lock = threading.Lock()
    done_count = done

    def finish(count):
        if dropped["n"] and count == done and not skipped["n"]:
            raise GenError("生图接口错误：Upstream request failed")
        parts = []
        if skipped["n"]:
            parts.append("有 %s 张接口回了文字、没有图片" % skipped["n"])
        if dropped["n"]:
            parts.append("有 %s 张上游没有接住" % dropped["n"])
        if parts:
            raise GenError("，".join(parts) + "，其余已落盘。")
        return count

    def run_one(job):
        folder, index, prompt, size = job
        try:
            shot = _edit_shot(editor, reference, prompt, size)
        except Exception as exc:
            if _chat_reply(exc):
                return "chat"
            if _upstream_drop(exc):
                return "upstream"
            raise
        (folder / ("%s.jpg" % index)).write_bytes(_as_jpeg(shot))
        return "ok"

    pending = list(jobs)
    for attempt in range(_UPSTREAM_TRIES):
        if not pending:
            break
        if attempt:
            time.sleep(_UPSTREAM_PAUSE)
        pass_width = width
        again = []
        hard = {"error": None}

        def run(job, _again=again, _width=pass_width):
            nonlocal done_count
            if on_progress and _width == 1:
                on_progress(done_count, total)
            try:
                kind = run_one(job)
            except Exception as exc:
                with lock:
                    if hard["error"] is None:
                        hard["error"] = exc
                return
            if kind == "ok":
                with lock:
                    done_count += 1
                    current = done_count
                if on_progress:
                    on_progress(current, total)
                return
            if kind == "chat":
                with lock:
                    skipped["n"] += 1
                return
            with lock:
                _again.append(job)

        if pass_width == 1:
            for job in pending:
                run(job)
                if hard["error"] is not None:
                    raise hard["error"]
        else:
            if on_progress:
                on_progress(done_count, total)
            with ThreadPoolExecutor(max_workers=pass_width) as pool:
                list(pool.map(run, pending))
            if hard["error"] is not None:
                raise hard["error"]
        pending = again
    dropped["n"] = len(pending)
    return finish(done_count)


def generate_story(conn, root, sku, lang, editor, complete=None, ocr=None, on_progress=None, workers=1, only_missing=False):
    """Draw three main images and five detail images from the product photo.

    Detail copy comes from the product name and specs. Detail-page text is not read.
    only_missing keeps frames that already landed and draws just the gaps.
    """
    from shop.image_translate import catalog_file
    del ocr

    lang = str(lang or "").strip()
    if lang not in COMMERCE_LANGS:
        raise GenError("一次只能选一种语言。")
    if only_missing and not missing_story_slots(root, sku, lang):
        return 8
    row = conn.execute(
        "select * from products where sku = ?",
        (sku,),
    ).fetchone()
    if row is None:
        raise GenError("没有这个商品。")
    keys = set(row.keys())
    try:
        listing = json.loads(row["listing"] or "{}") if "listing" in keys else {}
    except json.JSONDecodeError:
        listing = {}
    detail_urls = []
    if isinstance(listing, dict):
        for url in listing.get("detail_images") or []:
            if url and url not in detail_urls:
                detail_urls.append(url)
    detail_paths = []
    for url in detail_urls:
        path = catalog_file(url, root)
        if path is not None:
            detail_paths.append(path)
    hero = catalog_file(row["image_url"] if "image_url" in keys else "", root)
    if hero is None and detail_paths:
        hero = detail_paths[0]
    if hero is None:
        raise GenError("这个商品没有可参考的图。")
    try:
        offers = json.loads(row["offers"] or "[]") if "offers" in keys else []
    except json.JSONDecodeError:
        offers = []
    labels = []
    for offer in offers if isinstance(offers, list) else []:
        if not isinstance(offer, dict):
            continue
        label = offer.get("label") or ""
        if isinstance(label, dict):
            label = label.get(lang) or label.get("en") or ""
        label = str(label or "").strip()
        if label and label not in labels:
            labels.append(label)
    name = _json_text(row["names"] if "names" in keys else "", "en")
    specs = _json_text(row["specs"] if "specs" in keys else "", "en")
    detail_text = ""
    source = "\n".join(part for part in (name, specs, detail_text, " | ".join(labels)) if part)
    facts = _tighten_facts(story_fact_sheet(name, specs, detail_text, labels), complete)
    picture = "\n".join(
        part for part in (
            ("Product: %s" % name) if str(name or "").strip() else "",
            ("Specs: %s" % specs) if str(specs or "").strip() else "",
            _set_lines(detail_text),
        )
        if part
    )[:400]
    panels = story_panels(source)
    reference = Path(hero).read_bytes()
    (Path(root) / "static" / "catalog" / str(sku) / lang / "story").mkdir(parents=True, exist_ok=True)
    (Path(root) / "static" / "catalog" / str(sku) / lang / "story" / "facts.txt").write_text(facts, encoding="utf-8")
    main_folder = Path(root) / "static" / "catalog" / str(sku) / lang / "main"
    story_folder = Path(root) / "static" / "catalog" / str(sku) / lang / "story"
    jobs = [
        (
            main_folder,
            role[0],
            main_prompt(lang, picture, role, [item[1] for item in MAIN_ROLES[: role[0] - 1]]),
            MAIN_SIZE,
        )
        for role in MAIN_ROLES
    ]
    previous = []
    for index, panel in enumerate(panels, start=1):
        jobs.append((
            story_folder,
            index,
            story_prompt(lang, story_panel_facts(panel, name, specs, detail_text), panel, previous),
            STORY_SIZE,
        ))
        previous.append(panel["title"])
    if only_missing:
        jobs = [job for job in jobs if not (job[0] / ("%s.jpg" % job[1])).is_file()]
        if not jobs:
            return 8
    return _write_jobs(
        editor,
        reference,
        jobs,
        on_progress,
        done=0,
        total=len(jobs),
        workers=workers,
        replace=not only_missing,
    )
