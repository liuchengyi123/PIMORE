DECAY = 0.3


def decayed(rows, decay=DECAY):
    bases = {}
    order = []
    for sku, weight in rows:
        if sku in bases:
            continue
        bases[sku] = weight
        order.append(sku)
    return {sku: bases[sku] * (decay ** index) for index, sku in enumerate(order)}


def note_click(conn, email, sku, weight, keep=80):
    if not email or not sku:
        return
    conn.execute(
        "insert into clicks (email, sku, weight) values (?, ?, ?)",
        (email, sku, int(weight)),
    )
    conn.execute(
        """
        delete from clicks
        where email = ?
          and id not in (
            select id from clicks where email = ? order by id desc limit ?
          )
        """,
        (email, email, keep),
    )


def account_weights(conn, email, limit=40):
    if not email:
        return {}
    rows = conn.execute(
        "select sku, weight from clicks where email = ? order by id desc limit ?",
        (email, limit),
    ).fetchall()
    return decayed((row["sku"], row["weight"]) for row in rows)


def merge_weights(*maps, history=(), cart_skus=(), by_sku=None, cart_boost=4.0):
    """Combine account + guest + history position; cart SKUs boost their categories later via choose/for_you.
    Newer history entries (earlier in list) get higher positional weight.
    """
    out = {}
    for mapping in maps:
        for sku, weight in (mapping or {}).items():
            if not sku:
                continue
            try:
                w = float(weight)
            except (TypeError, ValueError):
                continue
            if w <= 0:
                continue
            out[sku] = out.get(sku, 0.0) + w
    for index, sku in enumerate(history or ()):
        if not sku:
            continue
        out[sku] = out.get(sku, 0.0) + max(1.0, 14.0 - index)
    if by_sku and cart_skus:
        cats = set()
        for sku in cart_skus:
            row = by_sku.get(sku) or by_sku.get(str(sku).split("~", 1)[0])
            if row is not None and row.get("category"):
                cats.add(row["category"])
        if cats:
            for sku, row in by_sku.items():
                if row.get("category") in cats and sku not in out:
                    # soft prior so cart category siblings can surface even without clicks
                    out[sku] = out.get(sku, 0.0) + 0.15
                elif row.get("category") in cats:
                    out[sku] = out.get(sku, 0.0) + cart_boost
    return out
