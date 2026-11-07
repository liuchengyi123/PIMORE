def gap(merchandise_cents, free_shipping_cents, tiers):
    ordered = sorted((int(threshold), int(off)) for threshold, off in tiers)
    goals = [("deal", threshold, off) for threshold, off in ordered]
    goals.append(("ship", int(free_shipping_cents), 0))
    goals.sort(key=lambda item: (item[1], 0 if item[0] == "deal" else 1))
    for kind, target, save in goals:
        if merchandise_cents < target:
            return (kind, target - merchandise_cents, save, target)
    best = ordered[-1][1] if ordered else 0
    last = goals[-1][1] if goals else 0
    return ("done", 0, best, last)

def fit_add(items, categories, need):
    need = int(need)
    under = [item for item in items if 0 < int(item["price_cents"]) <= need]
    if categories:
        same = [item for item in under if item.get("category") in categories]
        if same:
            under = same
    if not under:
        return None
    under.sort(key=lambda item: int(item["price_cents"]), reverse=True)
    return under[0]

def for_you(items, interest=None, taste=None, limit=8):
    interest = interest or {}
    taste = taste or {}
    by_sku = {item["sku"]: item for item in items}
    anchors = [
        (by_sku[sku]["category"], by_sku[sku]["price_cents"], weight)
        for sku, weight in interest.items()
        if sku in by_sku
    ]
    if anchors:
        ranked = []
        for item in items:
            if item["stock"] <= 0 or item["sku"] in interest:
                continue
            score = 0
            for category, price, weight in anchors:
                if item["category"] != category:
                    continue
                span = max(price, 100)
                closeness = 1 - min(1, abs(item["price_cents"] - price) / span)
                score = max(score, weight * (4 + 12 * closeness))
            if score:
                ranked.append((score, item))
        ranked.sort(key=lambda row: row[0], reverse=True)
        if ranked:
            return [row[1] for row in ranked[:limit]]
    if not taste or not any(taste.values()):
        return []
    cats = [cat for cat, qty in sorted(taste.items(), key=lambda item: -item[1]) if qty > 0]
    pools = [
        [item for item in items if item["category"] == cat and item["stock"] > 0]
        for cat in cats
    ]
    if not pools or not pools[0]:
        return []
    picked = []
    top_take = min(len(pools[0]), max(4, limit // 2))
    picked.extend(pools[0][:top_take])
    pools[0] = pools[0][top_take:]
    while len(picked) < limit:
        grew = False
        for pool in pools:
            if pool and len(picked) < limit:
                picked.append(pool.pop(0))
                grew = True
        if not grew:
            break
    return picked

def choose(items, *, exclude, anchors=(), taste=None, touched=(), budget=None, limit=6):
    taste = taste or {}
    anchor_cats = {item["category"] for item in anchors}
    ranked = []
    for item in items:
        if item["sku"] in exclude or item["stock"] <= 0:
            continue
        score = taste.get(item["category"], 0) * 2
        if item["category"] in anchor_cats:
            score += 6
        near = 0
        for profile in touched:
            if profile["category"] != item["category"]:
                continue
            span = max(profile["price_cents"], 100)
            closeness = 1 - min(1, abs(item["price_cents"] - profile["price_cents"]) / span)
            near = max(near, profile["weight"] * closeness)
        score += near * 8
        price = item["price_cents"]
        if budget:
            if price <= budget:
                score += 40 + int(20 * price / budget)
            else:
                score -= 8
        ranked.append((score, price, item["sku"], item))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [row[3] for row in ranked[:limit]]

def _jitter(sku, salt):
    n = (int(salt) & 0xFFFFFFFF) ^ 0x9E3779B9
    for ch in str(sku):
        n = (n * 33 + ord(ch)) & 0xFFFFFFFF
    return (n % 1000) / 1000.0

BROWSE_SHARE = 0.4  # personalized slots; remainder is system-random across categories

def _interest_categories(interest, catalog, taste=None):
    weights = category_weights(interest, catalog, taste)
    return {cat for cat, weight in weights.items() if float(weight or 0) > 0}


def _heavy_categories(interest, catalog, taste=None, top=2):
    weights = category_weights(interest, catalog, taste)
    if not weights:
        return set()
    return set(sorted(weights, key=lambda key: (-weights.get(key, 0.0), key))[: max(1, int(top or 2))])


def _pick_diverse_pool(items, *, used=(), avoid=(), heavy=()):
    """Prefer items outside browse cats; fall back to skipping only strongest interest."""
    used = {str(sku) for sku in (used or ()) if sku}
    avoid = set(avoid or ())
    heavy = set(heavy or ())
    base = [item for item in items if item.get("sku") and str(item["sku"]) not in used]
    if not base:
        return []
    strict = [item for item in base if (item.get("category") or "") not in avoid]
    if strict:
        return strict
    soft = [item for item in base if (item.get("category") or "") not in heavy]
    return soft or list(base)


def _interleave_browse(
    personal,
    diverse,
    *,
    share,
    limit,
    interest_cats=(),
    filler=(),
):
    """Hard-cap interest-category share near browse_share; diverse slots never take interest cats first."""
    from collections import deque

    interest_cats = set(interest_cats or ())
    limit = max(1, int(limit or 1))
    share = max(0.0, min(1.0, float(share)))
    max_interest = int(round(limit * share)) if interest_cats else 0
    personal_q = deque(personal or ())
    diverse_q = deque(diverse or ())
    filler_q = deque(filler or ())
    per_ten = max(0, min(10, int(round(share * 10)))) if personal_q else 0
    personal_slots = set()
    if per_ten:
        for i in range(per_ten):
            personal_slots.add(int(i * 10 / per_ten) % 10)
    pattern = [i in personal_slots for i in range(10)] if personal_q else [False] * 10
    out = []
    seen = set()
    interest_n = 0
    step = 0

    def take_from(queue, *, allow_interest):
        nonlocal interest_n
        while queue:
            item = queue.popleft()
            sku = item.get("sku")
            if not sku or sku in seen:
                continue
            cat = item.get("category") or ""
            is_interest = bool(interest_cats) and cat in interest_cats
            if is_interest and not allow_interest:
                continue
            if is_interest and interest_n >= max_interest:
                continue
            seen.add(sku)
            if is_interest:
                interest_n += 1
            return item
        return None

    while len(out) < limit:
        prefer_personal = pattern[step % 10] if personal_q or max_interest else False
        step += 1
        picked = None
        if prefer_personal and interest_n < max_interest:
            picked = take_from(personal_q, allow_interest=True)
            if picked is None:
                picked = take_from(diverse_q, allow_interest=False)
        else:
            picked = take_from(diverse_q, allow_interest=False)
            if picked is None:
                picked = take_from(filler_q, allow_interest=False)
            if picked is None and interest_n < max_interest:
                picked = take_from(personal_q, allow_interest=True)
        if picked is None:
            picked = take_from(filler_q, allow_interest=False)
        if picked is None:
            picked = take_from(personal_q, allow_interest=interest_n < max_interest)
        if picked is None:
            break
        out.append(picked)

    if len(out) < limit:
        for item in list(diverse_q) + list(filler_q) + list(personal_q):
            if len(out) >= limit:
                break
            sku = item.get("sku")
            if not sku or sku in seen:
                continue
            cat = item.get("category") or ""
            is_interest = bool(interest_cats) and cat in interest_cats
            if is_interest and interest_n >= max_interest:
                continue
            seen.add(sku)
            if is_interest:
                interest_n += 1
            out.append(item)
    return out[:limit]


def diverse_order(items, *, salt=0, exclude=(), heat=None, prior=None, boost=None, limit=None):
    """System random across categories. No browse interest. Stable for a given salt."""
    exclude = {str(sku) for sku in (exclude or ()) if sku}
    heat = heat or {}
    prior = prior or {}
    boost = boost or {}
    buckets = {}
    for item in items:
        sku = item.get("sku")
        if not sku or str(sku) in exclude:
            continue
        if int(item.get("stock") or 0) <= 0:
            continue
        buckets.setdefault(item.get("category") or "", []).append(item)
    if not buckets:
        for item in items:
            sku = item.get("sku")
            if not sku or str(sku) in exclude:
                continue
            buckets.setdefault(item.get("category") or "", []).append(item)
    for cat, pool_items in list(buckets.items()):
        pool_items.sort(
            key=lambda item: (
                -float(boost.get(item["sku"], 0) or 0),
                -min(float(heat.get(item["sku"], 0) or 0), 100.0) * 0.04,
                int(prior.get(item["sku"], 1) or 0),
                _jitter(item["sku"], salt),
                str(item.get("sku") or ""),
            )
        )
    keys = sorted(buckets)
    if keys:
        start = abs(int(salt)) % len(keys)
        keys = keys[start:] + keys[:start]
    result = []
    seen = set()
    while buckets and (limit is None or len(result) < int(limit)):
        progressed = False
        for cat in list(keys):
            pool_items = buckets.get(cat) or []
            while pool_items:
                item = pool_items.pop(0)
                sku = item.get("sku")
                if not sku or sku in seen:
                    continue
                seen.add(sku)
                result.append(item)
                progressed = True
                break
            if not pool_items and cat in buckets:
                del buckets[cat]
            if limit is not None and len(result) >= int(limit):
                break
        if not progressed:
            break
        keys = [key for key in keys if key in buckets]
    return result

def blend_order(
    items,
    *,
    interest=None,
    catalog=(),
    cart_skus=(),
    taste=None,
    salt=0,
    heat=None,
    prior=None,
    boost=None,
    browse_share=BROWSE_SHARE,
    exclude=(),
):
    """~browse_share from personal ranking; the rest diversify across categories."""
    exclude = {str(sku) for sku in (exclude or ()) if sku}
    pool = [item for item in items if item.get("sku") and str(item["sku"]) not in exclude]
    if not pool:
        return []
    share = max(0.0, min(1.0, float(browse_share)))
    personal = personal_order(
        pool,
        interest=interest,
        catalog=catalog or pool,
        cart_skus=cart_skus,
        taste=taste,
        salt=salt,
        heat=heat,
        prior=prior,
        boost=boost,
    )
    interest_cats = _interest_categories(interest, catalog or pool, taste)
    heavy = _heavy_categories(interest, catalog or pool, taste, top=2)
    diverse_pool = _pick_diverse_pool(pool, avoid=interest_cats, heavy=heavy)
    diverse = diverse_order(
        diverse_pool,
        salt=(int(salt) ^ 0xA5A5A5A5) & 0xFFFFFFFF,
        heat=heat,
        prior=prior,
        boost=boost,
    )
    filler = diverse_order(
        pool,
        salt=(int(salt) ^ 0x5A5A5A5A) & 0xFFFFFFFF,
        heat=heat,
        prior=prior,
        boost=boost,
    )
    # Full shelf order: enforce share over a rolling window via interleave, then append remainder.
    head = _interleave_browse(
        personal,
        diverse,
        share=share,
        limit=len(pool),
        interest_cats=interest_cats,
        filler=filler,
    )
    seen = {item["sku"] for item in head}
    for item in personal:
        sku = item.get("sku")
        if sku and sku not in seen:
            head.append(item)
            seen.add(sku)
    return head

def ranked_for_you(
    items,
    interest=None,
    taste=None,
    limit=8,
    salt=0,
    pool=24,
    browse_share=BROWSE_SHARE,
    exclude=(),
):
    """Browse-weighted picks (~browse_share) mixed with cross-category random fill."""
    exclude = {str(sku) for sku in (exclude or ()) if sku}
    stocked = [
        item
        for item in items
        if int(item.get("stock") or 0) > 0 and item.get("sku") and str(item["sku"]) not in exclude
    ]
    if not stocked:
        stocked = [item for item in items if item.get("sku") and str(item["sku"]) not in exclude]
    if not stocked:
        return []
    limit = max(1, int(limit or 8))
    share = max(0.0, min(1.0, float(browse_share)))
    interest_cats = _interest_categories(interest, stocked, taste)
    heavy = _heavy_categories(interest, stocked, taste, top=2)
    personal_n = int(round(limit * share)) if (interest or taste) else 0
    personal = []
    if personal_n:
        base = for_you(stocked, interest=interest, taste=taste, limit=max(personal_n, int(pool or personal_n)))
        if base:
            scored = []
            for index, item in enumerate(base):
                jitter = (abs(hash((item["sku"], int(salt)))) % 1000) / 1000.0
                scored.append((len(base) - index + jitter, item))
            scored.sort(key=lambda row: row[0], reverse=True)
            personal = [row[1] for row in scored[:personal_n]]
    used = {item["sku"] for item in personal}
    diverse_pool = _pick_diverse_pool(stocked, used=used, avoid=interest_cats, heavy=heavy)
    random_fill = diverse_order(
        diverse_pool,
        salt=(int(salt) ^ 0x51515151) & 0xFFFFFFFF,
        exclude=used,
        limit=max(limit * 3, limit),
    )
    filler = diverse_order(
        stocked,
        salt=(int(salt) ^ 0xC3C3C3C3) & 0xFFFFFFFF,
        exclude=used,
        limit=max(limit * 3, limit),
    )
    out = _interleave_browse(
        personal,
        random_fill,
        share=share,
        limit=limit,
        interest_cats=interest_cats,
        filler=filler,
    )
    if len(out) < limit:
        extra = diverse_order(stocked, salt=salt, exclude={item["sku"] for item in out}, limit=limit - len(out))
        out.extend(extra)
    return out[:limit]

def category_weights(interest, catalog, taste=None):
    """How strongly this visitor leans toward each category."""
    by_sku = {row["sku"]: row for row in catalog}
    weights = {}
    for key, qty in (taste or {}).items():
        try:
            weights[key] = float(qty)
        except (TypeError, ValueError):
            continue
    for sku, weight in (interest or {}).items():
        row = by_sku.get(sku)
        if row is None:
            continue
        cat = row.get("category") or ""
        if not cat:
            continue
        try:
            weights[cat] = weights.get(cat, 0.0) + float(weight)
        except (TypeError, ValueError):
            continue
    return weights

def personal_order(items, *, interest=None, catalog=(), cart_skus=(), taste=None, salt=0, heat=None, prior=None, boost=None):
    """Every item stays in the list. Liked category, subcategory, and price come first.
    The order depends only on salt, so page 2 continues page 1.
    """
    interest = interest or {}
    heat = heat or {}
    prior = prior or {}
    boost = boost or {}
    cart = set(cart_skus or ())
    by_sku = {row["sku"]: row for row in catalog}
    cat_w = {}
    sub_w = {}
    anchors = []
    for key, qty in (taste or {}).items():
        try:
            cat_w[key] = float(qty)
        except (TypeError, ValueError):
            continue
    for sku, weight in interest.items():
        try:
            w = float(weight)
        except (TypeError, ValueError):
            continue
        if w <= 0:
            continue
        row = by_sku.get(sku)
        if row is None:
            continue
        cat = row.get("category") or ""
        sub = row.get("subcategory") or ""
        if cat:
            cat_w[cat] = cat_w.get(cat, 0.0) + w
        if cat and sub:
            sub_w[(cat, sub)] = sub_w.get((cat, sub), 0.0) + w
        anchors.append((cat, int(row.get("price_cents") or 0), w, sku))
    def score_of(item):
        sku = item["sku"]
        cat = item.get("category") or ""
        sub = item.get("subcategory") or ""
        price = int(item.get("price_cents") or 0)
        score = float(cat_w.get(cat, 0.0)) * 20.0
        score += float(sub_w.get((cat, sub), 0.0)) * 6.0
        near = 0.0
        for acat, aprice, aw, asku in anchors:
            if acat != cat or asku == sku:
                continue
            span = max(int(aprice), 100)
            closeness = 1 - min(1.0, abs(price - int(aprice)) / span)
            near = max(near, float(aw) * closeness)
        score += near * 12.0
        if sku in interest:
            score -= 25.0
        if sku in cart:
            score -= 200.0
        if not str(item.get("image_url") or "").strip():
            score -= 1.5
        hot = float(heat.get(sku, 0) or 0)
        score += min(hot, 100.0) * 0.04
        rank_n = int(prior.get(sku, 1) or 0)
        if rank_n <= 0:
            score += 1.0
        score += float(boost.get(sku, 0) or 0)
        score += _jitter(sku, salt) * 0.3
        return score
    decorated = []
    for item in items:
        stock = int(item.get("stock") or 0)
        decorated.append((1 if stock <= 0 else 0, -score_of(item), str(item.get("sku") or "")))
    order = sorted(range(len(decorated)), key=lambda i: decorated[i])
    return [items[i] for i in order]

def ranked_choose(items, *, exclude, anchors=(), taste=None, touched=(), budget=None, limit=6, salt=0, pool=18):
    picked = choose(
        items,
        exclude=exclude,
        anchors=anchors,
        taste=taste,
        touched=touched,
        budget=budget,
        limit=max(limit, pool),
    )
    if not picked:
        return []
    scored = []
    for index, item in enumerate(picked):
        jitter = (abs(hash((item["sku"], int(salt)))) % 1000) / 1000.0
        scored.append(((len(picked) - index) + jitter, item))
    scored.sort(key=lambda row: row[0], reverse=True)
    return [row[1] for row in scored[:limit]]
