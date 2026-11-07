import io
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageOps

PHOTO_EDGE = 1600
DETAIL_WIDTH = 2200
DETAIL_HEIGHT = 4400
JPEG_QUALITY = 85
CARD_EDGE = 640
CARD_QUALITY = 80


def safe_image_url(url):
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "0.0.0.0"} or host.endswith(".local"):
        return False
    if host == "127.0.0.1" or host.startswith("127."):
        return False
    if host.startswith("10.") or host.startswith("192.168.") or host.startswith("169.254."):
        return False
    parts = host.split(".")
    if len(parts) == 4 and all(part.isdigit() for part in parts):
        first, second = int(parts[0]), int(parts[1])
        if first == 172 and 16 <= second <= 31:
            return False
    return True


def image_extension(data):
    if data.startswith(b"\xff\xd8"):
        return ".jpg"
    if data.startswith(b"\x89PNG"):
        return ".png"
    if data.startswith(b"GIF8"):
        return ".gif"
    if data.startswith(b"RIFF") and b"WEBP" in data[:16]:
        return ".webp"
    return ""


def _has_alpha(image):
    if image.mode in {"RGBA", "LA"}:
        return True
    return image.mode == "P" and "transparency" in image.info


def prepare_image(data, kind="photo"):
    if not data:
        return data
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except Exception:
        return data
    if getattr(image, "n_frames", 1) > 1:
        return data
    image = ImageOps.exif_transpose(image)
    width, height = image.size
    if kind == "detail":
        scale = min(1.0, DETAIL_WIDTH / width, DETAIL_HEIGHT / height)
    else:
        scale = min(1.0, PHOTO_EDGE / max(width, height))
    if scale < 1:
        image = image.resize(
            (max(1, round(width * scale)), max(1, round(height * scale))),
            Image.Resampling.LANCZOS,
        )
    out = io.BytesIO()
    if _has_alpha(image):
        image.convert("RGBA").save(out, format="PNG")
    else:
        image.convert("RGB").save(
            out,
            format="JPEG",
            quality=JPEG_QUALITY,
            subsampling=0 if kind == "detail" else 2,
        )
    cooked = out.getvalue()
    if scale == 1 and len(cooked) >= len(data):
        return data
    return cooked


PHONE_EDGE = 960
PHONE_QUALITY = 82


def card_image(url, root):
    return fitted_image(url, root, CARD_EDGE, "card", CARD_QUALITY, 120_000)


def phone_image(url, root):
    return fitted_image(url, root, PHONE_EDGE, "view", PHONE_QUALITY, 160_000)


def fitted_image(url, root, edge, folder, quality, skip_under):
    text = str(url or "")
    if not text.startswith("/static/catalog/") or "/card/" in text or "/view/" in text:
        return url
    path = Path(root) / "static" / text[len("/static/"):]
    if not path.is_file():
        return url
    if max(path.stat().st_size, 1) <= skip_under and path.suffix.lower() in {".jpg", ".jpeg"}:
        try:
            with Image.open(path) as image:
                longest = max(image.size)
            if longest <= edge:
                return url
        except Exception:
            return url
    dest = path.parent / folder / f"{path.stem}.jpg"
    try:
        if not dest.is_file() or dest.stat().st_mtime < path.stat().st_mtime:
            cooked = _fit_bytes(path.read_bytes(), edge, quality)
            if not cooked:
                return url
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(cooked)
    except Exception:
        return url
    relative = dest.relative_to(Path(root) / "static").as_posix()
    return f"/static/{relative}"


def _fit_bytes(data, edge, quality):
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except Exception:
        return b""
    if getattr(image, "n_frames", 1) > 1:
        return b""
    image = ImageOps.exif_transpose(image)
    width, height = image.size
    scale = min(1.0, edge / max(width, height))
    if scale < 1:
        image = image.resize(
            (max(1, round(width * scale)), max(1, round(height * scale))),
            Image.Resampling.LANCZOS,
        )
    if _has_alpha(image):
        flat = Image.new("RGB", image.size, (255, 255, 255))
        rgba = image.convert("RGBA")
        flat.paste(rgba, mask=rgba.split()[-1])
        image = flat
    out = io.BytesIO()
    image.convert("RGB").save(out, format="JPEG", quality=quality, subsampling=2)
    return out.getvalue()


def save_image_bytes(data, folder, index, max_bytes=4_000_000):
    if not data:
        return ""
    kind = "detail" if str(index).startswith("d") else "photo"
    cooked = prepare_image(data, kind)
    if max_bytes is not None and len(cooked) > max_bytes:
        return ""
    ext = image_extension(cooked)
    if not ext:
        return ""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{index}{ext}"
    (folder / name).write_bytes(cooked)
    return f"/static/catalog/{folder.name}/{name}"


def save_remote_image(url, folder, index):
    if not safe_image_url(url):
        return ""
    try:
        import httpx

        response = httpx.get(
            url,
            timeout=httpx.Timeout(8.0, connect=4.0),
            follow_redirects=False,
            headers={"User-Agent": "Harbor"},
        )
        response.raise_for_status()
    except Exception:
        return ""
    return save_image_bytes(response.content, folder, index)
