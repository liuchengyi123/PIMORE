"""Crop the platform chrome off each landing design and record tile hit areas.

Reads the untouched originals in static/lp-scenes/full when they exist.
Writes the cropped public image and shop/lp_scene_hits.py.
"""
from pathlib import Path

from PIL import Image, ImageDraw

from shop.taxonomy import CHILDREN

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "static" / "lp-scenes"
FULL = SRC / "full"


def row_stats(px, w, y):
    rs = gs = bs = n = 0
    for x in range(0, w, 6):
        r, g, b = px[x, y]
        rs += r
        gs += g
        bs += b
        n += 1
    rs //= n
    gs //= n
    bs //= n
    acc = white = 0
    for x in range(0, w, 6):
        r, g, b = px[x, y]
        acc += abs(r - rs) + abs(g - gs) + abs(b - bs)
        if r > 250 and g > 250 and b > 250:
            white += 1
    return acc // n, white / n


def columns(px, w, top, bottom):
    y0 = top + int((bottom - top) * 0.75)
    flags = []
    for x in range(w):
        white = n = 0
        for y in range(y0, max(y0 + 2, bottom), 2):
            r, g, b = px[x, y]
            n += 1
            if r > 250 and g > 250 and b > 250:
                white += 1
        flags.append(white / max(n, 1) > 0.75)
    cols = []
    x = 0
    while x < w:
        if flags[x]:
            x += 1
            continue
        start = x
        while x < w and not flags[x]:
            x += 1
        if x - start > 40:
            cols.append((max(0, start - 1), min(w - 1, x + 1)))
    return cols or [(8, w - 8)]


def subdivide(px, box):
    left, top, right, bottom = box
    y = top + (bottom - top) // 3
    runs = []
    start = None
    for x in range(left, right):
        r, g, b = px[x, y]
        white = r > 248 and g > 248 and b > 248
        if white and start is None:
            start = x
        elif not white and start is not None:
            if x - start >= 6:
                runs.append((start, x))
            start = None
    inner = [(a, b) for a, b in runs if a > left + 8 and b < right - 8]
    if not inner:
        return [box]
    edges = [left] + [(a + b) // 2 for a, b in inner] + [right]
    parts = []
    for i in range(len(edges) - 1):
        if edges[i + 1] - edges[i] > 30:
            parts.append((edges[i], top, edges[i + 1], bottom))
    return parts or [box]


def detect(path):
    image = Image.open(path).convert("RGB")
    w, h = image.size
    px = image.load()
    stats = [row_stats(px, w, y) for y in range(h)]
    photo = [v > 45 for v, _ in stats]
    spans = []
    y = 0
    while y < h:
        if not photo[y]:
            y += 1
            continue
        start = y
        while y < h and photo[y]:
            y += 1
        if y - start >= 70:
            spans.append((start, y - 1))
    hero = spans[0][0]
    boxes = []
    for top, bottom in spans[1:]:
        y = bottom + 1
        gap = 0
        end = bottom
        while y < h - 1 and y < bottom + 110:
            variance, white = stats[y]
            if white > 0.9 and variance < 14:
                gap += 1
                if gap >= 6:
                    end = y - gap
                    break
            else:
                gap = 0
                end = y
            y += 1
        for left, right in columns(px, w, top, end):
            boxes.append((left, top, right, end))
    need = len(CHILDREN[path.stem])
    boxes = [
        box for box in boxes
        if not (box[0] < 20 and box[2] > w * 0.75 and box[1] > h * 0.80)
    ]
    guard = 0
    while len(boxes) < need and guard < 6:
        guard += 1
        split_at = None
        parts = None
        for i, box in enumerate(boxes):
            candidate = subdivide(px, box)
            if len(candidate) > 1:
                split_at = i
                parts = candidate
                break
        if split_at is None:
            break
        boxes = boxes[:split_at] + parts + boxes[split_at + 1 :]
    while len(boxes) > need:
        left, top, right, bottom = boxes[-1]
        if right - left > w * 0.75 and top > h * 0.72:
            boxes.pop()
        else:
            break
    if len(boxes) != need:
        raise SystemExit(f"{path.stem}: found {len(boxes)} tiles, expected {need}")
    return image, hero, boxes


def main():
    FULL.mkdir(exist_ok=True)
    lines = [
        '"""Click targets on the cropped category landing images.',
        "",
        "Percentages are of the image the page shows. The platform header",
        "is already cropped off. Order matches taxonomy.CHILDREN.",
        '"""',
        "",
        "SCENE_HITS = {",
    ]
    check = SRC / "_check"
    check.mkdir(exist_ok=True)
    for category, slugs in CHILDREN.items():
        public = SRC / f"{category}.png"
        original = FULL / f"{category}.png"
        if not original.exists():
            original.write_bytes(public.read_bytes())
        image, hero, boxes = detect(original)
        cropped = image.crop((0, hero, image.width, image.height))
        cropped.save(public, format="PNG", optimize=True)
        preview = cropped.copy()
        draw = ImageDraw.Draw(preview)
        height = image.height - hero
        links = []
        for slug, (left, top, right, bottom) in zip(slugs, boxes):
            draw.rectangle((left, top - hero, right, bottom - hero), outline="red", width=2)
            box = {
                "id": slug,
                "l": round(left / image.width * 100, 2),
                "t": round((top - hero) / height * 100, 2),
                "w": round((right - left) / image.width * 100, 2),
                "h": round((bottom - top) / height * 100, 2),
            }
            links.append(box)
        preview.save(check / f"{category}-final.png")
        body = ",\n".join(
            "            {"
            + f'"id": "{hit["id"]}", "l": {hit["l"]}, "t": {hit["t"]}, "w": {hit["w"]}, "h": {hit["h"]}'
            + "}"
            for hit in links
        )
        lines.append(f'    "{category}": [')
        lines.append(body)
        lines.append("    ],")
        print(category, "cut", hero, "tiles", len(links), "height", height)
    lines.append("}")
    lines.append("")
    (ROOT / "lp_scene_hits.py").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
