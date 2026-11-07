import io

from PIL import Image

from shop.images import CARD_EDGE, DETAIL_WIDTH, PHONE_EDGE, PHOTO_EDGE, card_image, phone_image, prepare_image, safe_image_url, save_image_bytes


def test_local_and_private_image_urls_are_refused():
    assert safe_image_url("https://img.example/a.jpg") is True
    assert safe_image_url("http://127.0.0.1/a.jpg") is False
    assert safe_image_url("http://192.168.1.8/a.jpg") is False
    assert safe_image_url("file:///tmp/a.jpg") is False


def _png(width, height, color=(180, 40, 40), noise=False):
    image = Image.new("RGB", (width, height), color)
    if noise:
        import random

        pixels = [(random.randrange(256), random.randrange(256), random.randrange(256)) for _ in range(width * height)]
        image.putdata(pixels)
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def test_product_photo_is_shrunk_to_a_clear_jpeg():
    raw = _png(2048, 2048, noise=True)
    cooked = prepare_image(raw, "photo")
    assert cooked.startswith(b"\xff\xd8")
    assert len(cooked) < len(raw) / 5
    with Image.open(io.BytesIO(cooked)) as image:
        assert max(image.size) == PHOTO_EDGE


def test_detail_picture_keeps_desktop_text_width():
    raw = _png(2480, 4656, (240, 240, 240))
    cooked = prepare_image(raw, "detail")
    assert cooked.startswith(b"\xff\xd8")
    with Image.open(io.BytesIO(cooked)) as image:
        assert image.size[0] == DETAIL_WIDTH
        assert image.size[1] > PHOTO_EDGE


def test_transparent_png_stays_png():
    image = Image.new("RGBA", (1800, 900), (0, 0, 0, 0))
    out = io.BytesIO()
    image.save(out, format="PNG")
    cooked = prepare_image(out.getvalue(), "photo")
    assert cooked.startswith(b"\x89PNG")
    with Image.open(io.BytesIO(cooked)) as result:
        assert result.mode == "RGBA"
        assert max(result.size) == PHOTO_EDGE


def test_card_image_shrinks_a_large_photo(tmp_path):
    folder = tmp_path / "static" / "catalog" / "sku1"
    folder.mkdir(parents=True)
    Image.new("RGB", (1600, 1200), (20, 40, 60)).save(folder / "0.jpg", quality=90)
    url = card_image("/static/catalog/sku1/0.jpg", tmp_path)
    assert url == "/static/catalog/sku1/card/0.jpg"
    with Image.open(folder / "card" / "0.jpg") as saved:
        assert max(saved.size) <= CARD_EDGE
    again = card_image("/static/catalog/sku1/0.jpg", tmp_path)
    assert again == url
    phone = phone_image("/static/catalog/sku1/0.jpg", tmp_path)
    assert phone == "/static/catalog/sku1/view/0.jpg"
    with Image.open(folder / "view" / "0.jpg") as saved:
        assert max(saved.size) <= PHONE_EDGE


def test_unreadable_bytes_are_stored_unchanged(tmp_path):
    raw = b"\xff\xd8\xff\xd9"
    saved = save_image_bytes(raw, tmp_path, 0, max_bytes=None)
    assert saved.endswith("/0.jpg")
    assert (tmp_path / "0.jpg").read_bytes() == raw
