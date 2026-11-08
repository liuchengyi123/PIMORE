"""Storefront assortment rules: click heat, LP quotas, personalization, hot-list boost.

One settings row (``reco_rules``) drives all of these. Defaults apply until an
admin saves the form at ``/admin/reco``.

Heat shown on a product (关注热度) is:

    clicks × heat_per_click

``clicks`` is the number of ``visits`` rows with ``kind='product'`` for that
SKU. A product page records one such row. It is not the Amazon title-match
score and not a count of distinct people.

Amazon bestseller overlap (``shop.hot``) is only a cold-start / tie-break
boost, and only when ``hot_boost`` is on.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from shop.lp_modules import IMPULSE_MAX_CENTS, IMPULSE_MIN_CENTS

SETTING_KEY = "reco_rules"

# Cents. Head/hero prefers this mid band when a photo exists.
HERO_MIN_CENTS = 300
HERO_MAX_CENTS = 800
UNDER3_MAX_CENTS = 299
BAND_3_5_MAX_CENTS = 499

DEFAULTS: dict[str, Any] = {
    # 1 product open → +98 关注热度. 2 opens → 196.
    "heat_per_click": 98,
    # LP never sorts by price. 1 = jitter around heat, 0 = stable heat order.
    "lp_shuffle": 1,
    "lp_max_cards": 24,
    # Of those cards, at most this many may be under $3.
    "lp_under3_cap": 6,
    # Fill at least this many from $3–$5 and $5–$10 when the pool has them.
    "lp_band_3_5_min": 6,
    "lp_band_5_10_min": 6,
    # Same subcategory at most this many times. 0 turns the cap off.
    "lp_sub_cap": 2,
    # Share of home/feed slots taken from browse interest. Rest is cross-category.
    "browse_share": 0.40,
    # Interest/history/taste rows required before those personal slots turn on.
    "personal_min_signals": 1,
    # Cold start: boost in-catalog products that match scraped hot titles.
    "hot_boost": 1,
    # Points added per title-match point. 2 × 12 = 24, below one click of 98.
    "hot_weight": 12.0,
}


class RecoConfigError(ValueError):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def heat_points(clicks, per_click) -> int:
    """关注热度. Units are heat points, not people and not cents.

    1 recorded product open with the default multiplier is 98.
    2 opens are 196.
    """
    try:
        n = int(clicks or 0)
    except (TypeError, ValueError):
        n = 0
    try:
        unit = int(per_click or 0)
    except (TypeError, ValueError):
        unit = 0
    if n < 0 or unit < 0:
        return 0
    return n * unit


def click_counts(conn) -> dict[str, int]:
    """All product-open rows, grouped by SKU. Callers should cache this."""
    found = {}
    rows = conn.execute(
        """
        select sku, count(*) as n
        from visits
        where kind = 'product' and sku != ''
        group by sku
        """
    ).fetchall()
    for row in rows:
        sku = str(row["sku"] or "")
        if sku:
            found[sku] = int(row["n"] or 0)
    return found


def click_count(conn, sku) -> int:
    parent = str(sku or "").split("~", 1)[0][:80]
    if not parent:
        return 0
    row = conn.execute(
        """
        select count(*) as n
        from visits
        where kind = 'product' and sku = ?
        """,
        (parent,),
    ).fetchone()
    return int(row["n"] or 0) if row is not None else 0


def _as_int(value, label, low, high) -> int:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        raise RecoConfigError(f"{label} 需要整数。") from None
    if number < low or number > high:
        raise RecoConfigError(f"{label} 需要在 {low} 到 {high} 之间。")
    return number


def _as_float(value, label, low, high, places=2) -> float:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        raise RecoConfigError(f"{label} 需要数字。") from None
    if number < low or number > high:
        raise RecoConfigError(f"{label} 需要在 {low} 到 {high} 之间。")
    return round(number, places)


def _flag(value) -> int:
    if isinstance(value, (list, tuple)):
        value = value[-1] if value else 0
    text = str(value).strip().lower()
    return 1 if text in {"1", "true", "on", "yes"} else 0


def normalize(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    """Merge ``raw`` onto defaults and reject out-of-range numbers."""
    source = dict(DEFAULTS)
    if raw:
        source.update({key: raw[key] for key in DEFAULTS if key in raw})
    rules = {
        "heat_per_click": _as_int(source["heat_per_click"], "关注热度系数", 0, 10000),
        "lp_shuffle": _flag(source["lp_shuffle"]),
        "lp_max_cards": _as_int(source["lp_max_cards"], "落地页商品数", 4, 60),
        "lp_under3_cap": _as_int(source["lp_under3_cap"], "低价带上限", 0, 60),
        "lp_band_3_5_min": _as_int(source["lp_band_3_5_min"], "$3–$5 至少", 0, 60),
        "lp_band_5_10_min": _as_int(source["lp_band_5_10_min"], "$5–$10 至少", 0, 60),
        "lp_sub_cap": _as_int(source["lp_sub_cap"], "子类目上限", 0, 24),
        "browse_share": _as_float(source["browse_share"], "兴趣坑占比", 0.0, 1.0),
        "personal_min_signals": _as_int(source["personal_min_signals"], "开启千人千面的最少信号", 0, 100),
        "hot_boost": _flag(source["hot_boost"]),
        "hot_weight": _as_float(source["hot_weight"], "外部热销权重", 0.0, 500.0, places=1),
    }
    limit = rules["lp_max_cards"]
    if rules["lp_under3_cap"] > limit:
        raise RecoConfigError("低价带上限不能大于落地页商品数。")
    if rules["lp_band_3_5_min"] + rules["lp_band_5_10_min"] > limit:
        raise RecoConfigError("$3–$5 与 $5–$10 的保底之和不能大于落地页商品数。")
    if rules["lp_sub_cap"] > limit:
        raise RecoConfigError("子类目上限不能大于落地页商品数。")
    return rules


def load_rules(conn) -> dict[str, Any]:
    row = conn.execute(
        "select value from settings where key = ?",
        (SETTING_KEY,),
    ).fetchone()
    if row is None or not str(row["value"] or "").strip():
        return normalize(DEFAULTS)
    try:
        data = json.loads(row["value"])
    except (TypeError, json.JSONDecodeError):
        return normalize(DEFAULTS)
    if not isinstance(data, dict):
        return normalize(DEFAULTS)
    try:
        return normalize(data)
    except RecoConfigError:
        return normalize(DEFAULTS)


def save_rules(conn, raw: Mapping[str, Any]) -> dict[str, Any]:
    rules = normalize(raw)
    conn.execute(
        "insert into settings (key, value) values (?, ?) on conflict(key) do update set value = excluded.value",
        (SETTING_KEY, json.dumps(rules)),
    )
    return rules


def parse_form(source) -> dict[str, Any]:
    """Read the admin form. A checkbox wins over the hidden ``0`` before it."""

    def values(name):
        if hasattr(source, "getlist"):
            found = [str(item) for item in source.getlist(name)]
            if found:
                return found
        if isinstance(source, Mapping):
            raw = source.get(name, None)
        else:
            raw = source.get(name)
        if raw is None:
            return []
        if isinstance(raw, (list, tuple)):
            return [str(item) for item in raw]
        return [str(raw)]

    payload = dict(DEFAULTS)
    for key in DEFAULTS:
        found = values(key)
        if found:
            payload[key] = found[-1]
    return normalize(payload)


def personal_signals(interest=None, taste=None) -> int:
    """Rows that are real browse signals.

    Cart-category crumbs of 0.15 do not count. History and account clicks
    land here with weight >= 1.
    """
    count = 0
    for weight in (interest or {}).values():
        try:
            if float(weight) >= 1:
                count += 1
        except (TypeError, ValueError):
            continue
    for qty in (taste or {}).values():
        try:
            if float(qty) > 0:
                count += 1
        except (TypeError, ValueError):
            continue
    return count


def browse_share_for(interest, taste, rules) -> float:
    """0 when the visitor is still cold. Otherwise the configured share."""
    rules = rules or DEFAULTS
    if personal_signals(interest, taste) < int(rules.get("personal_min_signals") or 0):
        return 0.0
    try:
        share = float(rules.get("browse_share") if rules.get("browse_share") is not None else DEFAULTS["browse_share"])
    except (TypeError, ValueError):
        share = float(DEFAULTS["browse_share"])
    return max(0.0, min(1.0, share))


def _jitter(sku, salt) -> float:
    n = (int(salt) & 0xFFFFFFFF) ^ 0x9E3779B9
    for ch in str(sku):
        n = (n * 33 + ord(ch)) & 0xFFFFFFFF
    return (n % 1000) / 1000.0


def _price(row) -> int:
    try:
        return int(row.get("price_cents") or 0)
    except (TypeError, ValueError):
        return 0


def _sellable(row) -> bool:
    if not row or not row.get("sku"):
        return False
    if "published" in row and int(row.get("published") or 0) != 1:
        return False
    if "stock" in row and int(row.get("stock") or 0) <= 0:
        return False
    return True


def _band(cents: int) -> str:
    if cents <= UNDER3_MAX_CENTS:
        return "under_3"
    if cents <= BAND_3_5_MAX_CENTS:
        return "3_5"
    if cents <= IMPULSE_MAX_CENTS:
        return "5_10"
    return "above"


def _has_image(row) -> bool:
    return bool(str(row.get("image_url") or "").strip())


def related_hot_points(rows, title_scores, *, enabled, weight) -> dict[str, float]:
    """Cold-start boost from scraped bestseller titles.

    ``title_scores`` is the per-SKU overlap from ``shop.hot`` (title match).
    A product with no title hit still gets a small bump when another in-stock
    row in the same category did match, so related goods can surface.
    """
    weight = float(weight or 0)
    if not enabled or weight <= 0:
        return {}
    scores = title_scores or {}
    matched_cats = set()
    for row in rows:
        if not _sellable(row):
            continue
        if float(scores.get(row.get("sku")) or 0) > 0:
            cat = str(row.get("category") or "")
            if cat:
                matched_cats.add(cat)
    out = {}
    for row in rows:
        sku = row.get("sku")
        if not sku:
            continue
        title = float(scores.get(sku) or 0)
        extra = 0.0
        if title <= 0 and str(row.get("category") or "") in matched_cats:
            extra = 0.35
        points = round((title + extra) * weight, 4)
        if points:
            out[sku] = points
    return out


def assortment_heat(rows, clicks, title_scores, rules) -> dict[str, float]:
    """Rank heat = click points + optional external hot-list points."""
    rules = rules or DEFAULTS
    unit = int(rules.get("heat_per_click") or 0)
    clicks = clicks or {}
    hot = related_hot_points(
        rows,
        title_scores,
        enabled=bool(rules.get("hot_boost")),
        weight=rules.get("hot_weight") or 0,
    )
    out = {}
    for row in rows:
        sku = row.get("sku")
        if not sku:
            continue
        out[sku] = float(heat_points(clicks.get(sku, 0), unit)) + float(hot.get(sku, 0) or 0)
    return out


def _rank_score(row, heat, salt, shuffle, unit) -> float:
    sku = str(row.get("sku") or "")
    base = float((heat or {}).get(sku, 0) or 0)
    if shuffle:
        base += _jitter(sku, salt) * max(float(unit or 0), 1.0) * 0.35
    if _has_image(row):
        base += 0.01
    return base


def _ordered(rows, heat, salt, shuffle, unit):
    return sorted(
        rows,
        key=lambda row: (
            -_rank_score(row, heat, salt, shuffle, unit),
            str(row.get("sku") or ""),
        ),
    )


def _promote_hero(picked):
    def find(require_image):
        for index, row in enumerate(picked):
            cents = _price(row)
            if not (HERO_MIN_CENTS <= cents <= HERO_MAX_CENTS):
                continue
            if require_image and not _has_image(row):
                continue
            return index
        return None

    for require_image in (True, False):
        index = find(require_image)
        if index is None:
            continue
        if index:
            picked.insert(0, picked.pop(index))
        return picked
    return picked


def select_lp_rows(rows, *, clicks=None, title_scores=None, salt=0, rules=None):
    """Choose the /lp/ad grid.

    Impulse prices ($1–$10) are the pool, not the sort. Quotas keep the grid
    from becoming a wall of the cheapest SKUs. Click heat ranks inside a
    band; the external hot list is a smaller add-on.
    """
    rules = normalize(rules or DEFAULTS)
    sellable = [row for row in rows or [] if _sellable(row)]
    impulse = [
        row
        for row in sellable
        if IMPULSE_MIN_CENTS <= _price(row) <= IMPULSE_MAX_CENTS
    ]
    pool = impulse or sellable
    heat = assortment_heat(pool, clicks or {}, title_scores or {}, rules)
    unit = rules["heat_per_click"]
    shuffle = bool(rules["lp_shuffle"])
    ordered = _ordered(pool, heat, salt, shuffle, unit)
    limit = int(rules["lp_max_cards"])
    sub_cap = int(rules["lp_sub_cap"])
    min_mid = int(rules["lp_band_3_5_min"])
    min_high = int(rules["lp_band_5_10_min"])
    under_cap = int(rules["lp_under3_cap"])
    mins = {"3_5": min_mid, "5_10": min_high}

    def fill(respect_sub, respect_quota, respect_under):
        picked = []
        seen = set()
        sub_counts = {}
        taken = {"under_3": 0, "3_5": 0, "5_10": 0, "above": 0}
        for row in ordered:
            if len(picked) >= limit:
                break
            sku = row.get("sku")
            if not sku or sku in seen:
                continue
            band = _band(_price(row))
            if respect_under and band == "under_3" and taken["under_3"] >= under_cap:
                continue
            sub = str(row.get("subcategory") or "")
            if respect_sub and sub_cap > 0 and sub and sub_counts.get(sub, 0) >= sub_cap:
                continue
            if respect_quota:
                reserved = 0
                for name, minimum in mins.items():
                    if name == band:
                        continue
                    reserved += max(0, minimum - taken[name])
                short_self = max(0, mins.get(band, 0) - taken[band])
                if (limit - len(picked)) <= reserved and short_self <= 0:
                    continue
            picked.append(row)
            seen.add(sku)
            taken[band] += 1
            if sub:
                sub_counts[sub] = sub_counts.get(sub, 0) + 1
        return picked

    # Quotas and subcategory first. If that cannot fill the page, drop the
    # subcategory cap, then the band minimums. The under-$3 cap stays.
    picked = fill(True, True, True)
    if len(picked) < limit:
        picked = fill(False, True, True)
    if len(picked) < limit:
        picked = fill(False, False, True)
    return _promote_hero(picked)


def mix_price_bands(
    rows,
    heat,
    *,
    limit=8,
    under_cents=300,
    under_cap=3,
    salt=0,
    heat_unit=98,
    shuffle=True,
):
    """Walk heat order and stop once the cheap band hits ``under_cap``.

    Used for Deals and other cold shelves that used to follow insertion
    order (which reads as cheapest-first). The cap relaxes only if the
    dearer bands cannot fill ``limit``.
    """
    ranked = _ordered(
        [row for row in rows or [] if _sellable(row) and _price(row) > 0],
        heat,
        salt,
        shuffle,
        heat_unit,
    )
    picked = []
    seen = set()
    low = 0
    cap = max(0, int(under_cap))
    ceiling = max(1, int(limit))
    for row in ranked:
        if len(picked) >= ceiling:
            break
        if _price(row) < int(under_cents):
            if low >= cap:
                continue
            low += 1
        picked.append(row)
        seen.add(row.get("sku"))
    if len(picked) < ceiling:
        for row in ranked:
            sku = row.get("sku")
            if sku in seen:
                continue
            picked.append(row)
            seen.add(sku)
            if len(picked) >= ceiling:
                break
    return picked
