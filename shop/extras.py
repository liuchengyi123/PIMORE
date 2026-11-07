from shop.i18n import CATEGORIES
from shop.locale import shipping_tier

LOCALES = ("US", "CN", "TW", "HK", "GB", "CA", "DE", "FR", "ES", "PT", "BR", "MX", "JP")
COLORS = ("Black", "White", "Stone")

WINDOWS = {
    "USCA": ((5, 9), (3, 6)),
    "EU": ((8, 14), (5, 8)),
    "JP": ((6, 11), (4, 7)),
    "MXBR": ((9, 16), (6, 10)),
}


def read_skus(raw, limit=12):
    seen = []
    for part in (raw or "").split(","):
        sku = part.strip()
        if sku and sku not in seen:
            seen.append(sku)
    return seen[:limit]


def write_skus(skus, limit=12):
    return ",".join(read_skus(",".join(skus), limit))


def read_notes(raw):
    notes = {}
    for part in (raw or "").split(","):
        if "=" not in part:
            continue
        sku, color = part.split("=", 1)
        if sku.strip() and color.strip() in COLORS:
            notes[sku.strip()] = color.strip()
    return notes


def write_notes(notes):
    return ",".join(f"{sku}={color}" for sku, color in notes.items() if color in COLORS)


def read_taste(raw):
    counts = {}
    for part in (raw or "").split(","):
        if ":" not in part:
            continue
        key, qty = part.split(":", 1)
        key = key.strip()
        if key not in CATEGORIES:
            continue
        try:
            counts[key] = max(0, min(99, int(qty)))
        except ValueError:
            continue
    return counts


def write_taste(counts):
    pairs = sorted(
        ((key, qty) for key, qty in counts.items() if key in CATEGORIES and qty > 0),
        key=lambda item: (-item[1], item[0]),
    )
    return ",".join(f"{key}:{qty}" for key, qty in pairs)


def bump_taste(raw, category, weight=1):
    counts = read_taste(raw)
    if category not in CATEGORIES:
        return write_taste(counts)
    counts[category] = min(99, counts.get(category, 0) + weight)
    return write_taste(counts)


def read_interest(raw, limit=48):
    counts = {}
    for part in (raw or "").split(","):
        if ":" not in part:
            continue
        sku, qty = part.split(":", 1)
        sku = sku.strip()
        if not sku or len(sku) > 40 or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-" for ch in sku):
            continue
        try:
            counts[sku] = max(0, min(99, int(qty)))
        except ValueError:
            continue
    top = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return dict(top)


def bump_interest(raw, sku, weight=1, limit=48):
    counts = read_interest(raw, limit=limit)
    sku = (sku or "").strip()
    if not sku or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-" for ch in sku):
        return ",".join(f"{key}:{qty}" for key, qty in counts.items())
    counts[sku] = min(99, counts.get(sku, 0) + weight)
    top = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return ",".join(f"{key}:{qty}" for key, qty in top)


def delivery_span(country, speed="standard"):
    slow, fast = WINDOWS.get(shipping_tier(country), WINDOWS["USCA"])
    return fast if speed == "express" else slow
