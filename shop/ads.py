def load_ads(conn, lang):
    rows = conn.execute("select * from ads").fetchall()
    grouped = {}
    for row in rows:
        grouped.setdefault(row["slot"], {})[row["lang"]] = row
    chosen = {}
    for slot, versions in grouped.items():
        row = versions.get(lang) or versions.get("en")
        if row and _visible(slot, row):
            chosen[slot] = row
    return chosen


def _visible(slot, row):
    if slot == "announcement":
        return bool((row["body"] or "").strip())
    if slot in {"sponsored", "pdp-sponsored", "cart-recommend"}:
        return bool((row["href"] or "").strip())
    return bool((row["image_url"] or "").strip())


def sponsored_skus(ads, slot="sponsored"):
    row = ads.get(slot)
    if row is None:
        return []
    return [part.strip() for part in (row["href"] or "").split(",") if part.strip()]
