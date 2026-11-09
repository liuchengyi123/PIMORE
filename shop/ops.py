from datetime import datetime, timedelta, timezone

LANG_LABEL = {
    "en": "英语",
    "es": "西语",
    "de": "德语",
    "fr": "法语",
    "pt": "葡语",
    "ja": "日语",
}


def _today():
    return datetime.now(timezone.utc).date()


def product_interest_count(conn, sku):
    parent = str(sku or "").split("~", 1)[0][:80]
    if not parent:
        return 0
    row = conn.execute(
        """
        select count(distinct visitor) as n
        from visits
        where kind = 'product' and sku = ? and visitor != ''
        """,
        (parent,),
    ).fetchone()
    return int(row["n"] or 0)


def record(conn, kind, *, sku="", country="", lang="", visitor="", cents=0, qty=1):
    parent = str(sku or "").split("~", 1)[0][:80]
    conn.execute(
        """
        insert into visits (day, kind, sku, country, lang, visitor, cents, qty)
        values (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            _today().isoformat(),
            kind,
            parent,
            str(country or "").upper()[:2],
            str(lang or "")[:8],
            str(visitor or "")[:32],
            int(cents or 0),
            int(qty or 0),
        ),
    )


def note_paid(conn, order):
    lines = conn.execute(
        "select sku, price_cents, qty from order_lines where order_id = ?",
        (order["id"],),
    ).fetchall()
    record(conn, "sale", country=order["ship_country"], cents=int(order["due_cents"]), qty=1)
    for line in lines:
        record(
            conn,
            "paid",
            sku=line["sku"],
            country=order["ship_country"],
            cents=int(line["price_cents"]) * int(line["qty"]),
            qty=int(line["qty"]),
        )


def note_refund(conn, order, lines):
    record(conn, "refund", country=order["ship_country"], cents=int(order["due_cents"]), qty=1)
    for line in lines:
        record(conn, "return", sku=line["sku"], country=order["ship_country"], qty=int(line["qty"]))


def _span(days):
    picked = 30 if int(days) >= 30 else 1 if int(days) <= 1 else 7
    end = _today()
    start = end - timedelta(days=picked - 1)
    return picked, start.isoformat()


def _pair(conn, kind, start):
    row = conn.execute(
        "select count(*) as n, coalesce(sum(cents), 0) as cents from visits where kind = ? and day >= ?",
        (kind, start),
    ).fetchone()
    return int(row["n"]), int(row["cents"])


def _pct(curr, prev):
    if not prev:
        return None
    return round((curr - prev) * 100.0 / prev, 1)


def _nice_ceiling(value):
    value = int(value or 0)
    if value <= 0:
        return 1
    exp = 0
    probe = value
    while probe >= 10:
        probe //= 10
        exp += 1
    base = 10 ** exp
    for mult in (1, 2, 2.5, 5, 10):
        ceiling = mult * base
        if ceiling >= value:
            return int(ceiling)
    return value


def _money_tick(cents):
    dollars = int(cents or 0) / 100
    if dollars >= 1000:
        text = f"{dollars / 1000:.1f}".rstrip("0").rstrip(".")
        return f"${text}k"
    if dollars >= 100 or dollars == 0:
        return f"${dollars:.0f}"
    return f"${dollars:.2f}"


def _combo_chart(points, line_key, bar_key, *, money="right", show_line=True):
    """Geometry for a combo chart: bars plus an optional line, with axis ticks."""
    width, height = 720, 248
    pad_l = 46
    pad_r = 52 if money == "right" else 14
    pad_t, pad_b = 12, 30
    count = max(len(points), 1)
    inner_w = width - pad_l - pad_r
    inner_h = height - pad_t - pad_b
    raw_line = max((int(p.get(line_key) or 0) for p in points), default=0)
    raw_bar = max((int(p.get(bar_key) or 0) for p in points), default=0)
    max_line = _nice_ceiling(raw_line)
    max_bar = _nice_ceiling(raw_bar)
    baseline = pad_t + inner_h
    grids = []
    for step in range(5):
        y = baseline - (step / 4) * inner_h
        line_value = max_line * step / 4
        bar_value = max_bar * step / 4
        if money == "left":
            left = _money_tick(bar_value)
            right = ""
        else:
            left = str(int(round(line_value)))
            right = _money_tick(bar_value)
        grids.append({"y": round(y, 1), "left": left, "right": right})
    bars = []
    dots = []
    label_every = 1 if count <= 8 else 2 if count <= 16 else 5
    for index, point in enumerate(points):
        slot = inner_w / count
        bar_w = min(22, max(5, slot * 0.36))
        x = pad_l + slot * index + (slot - bar_w) / 2
        value = int(point.get(bar_key) or 0)
        bar_h = 0 if value <= 0 else max(2, (value / max_bar) * inner_h)
        bars.append({
            "x": round(x, 1),
            "y": round(baseline - bar_h, 1),
            "w": round(bar_w, 1),
            "h": round(bar_h, 1),
        })
        cx = pad_l + slot * index + slot / 2
        line_v = int(point.get(line_key) or 0)
        cy = baseline if not show_line else baseline - (line_v / max_line) * inner_h
        dots.append({
            "x": round(cx, 1),
            "y": round(cy, 1),
            "label": point.get("label") or "",
            "show": index % label_every == 0 or index == count - 1,
        })
    return {
        "w": width,
        "h": height,
        "baseline": round(baseline, 1),
        "plot_left": pad_l,
        "plot_right": width - pad_r,
        "grids": grids,
        "bars": bars,
        "dots": dots,
        "poly": " ".join(f"{dot['x']},{dot['y']}" for dot in dots),
        "show_line": show_line,
        "max_line": raw_line,
        "max_bar": raw_bar,
        "empty": raw_line == 0 and raw_bar == 0,
    }


def _group_trend(trend, mode):
    if mode == "day":
        return trend
    groups = {}
    order = []
    for point in trend:
        day = datetime.strptime(point["day"], "%Y-%m-%d").date()
        if mode == "week":
            year, week, _weekday = day.isocalendar()
            key = f"{year}-W{week:02d}"
            label = point["label"]
        else:
            key = day.strftime("%Y-%m")
            label = f"{day.month}月"
        bucket = groups.get(key)
        if bucket is None:
            bucket = {"day": point["day"], "label": label, "n": 0, "orders": 0, "sales": 0}
            groups[key] = bucket
            order.append(key)
        bucket["n"] += int(point.get("n") or 0)
        bucket["orders"] += int(point.get("orders") or 0)
        bucket["sales"] += int(point.get("sales") or 0)
    return [groups[key] for key in order]


def board(conn, days):
    picked, start = _span(days)
    cutoff = (_today() - timedelta(days=400)).isoformat()
    conn.execute("delete from visits where day < ?", (cutoff,))
    pages, _pages_cents = _pair(conn, "page", start)
    products, _product_cents = _pair(conn, "product", start)
    carts, _cart_cents = _pair(conn, "cart", start)
    orders, _order_cents = _pair(conn, "order", start)
    sales, sales_cents = _pair(conn, "sale", start)
    refunds, refund_cents = _pair(conn, "refund", start)
    visitors = int(
        conn.execute(
            """
            select count(distinct visitor) as n from visits
            where kind = 'page' and day >= ? and visitor != ''
            """,
            (start,),
        ).fetchone()["n"]
    )
    paid_orders = max(0, sales - refunds)
    paid_cents = sales_cents - refund_cents
    rate = "—" if visitors == 0 else f"{paid_orders * 100 / visitors:.1f}%"
    counted = {
        row["day"]: int(row["n"])
        for row in conn.execute(
            "select day, count(*) as n from visits where kind = 'page' and day >= ? group by day",
            (start,),
        ).fetchall()
    }
    peak = max(counted.values(), default=0)
    sale_days = {
        row["day"]: {"n": int(row["n"]), "cents": int(row["cents"] or 0)}
        for row in conn.execute(
            """
            select day, count(*) as n, coalesce(sum(cents), 0) as cents
            from visits where kind = 'sale' and day >= ?
            group by day
            """,
            (start,),
        ).fetchall()
    }
    start_day = datetime.strptime(start, "%Y-%m-%d").date()
    trend = []
    for offset in range(picked):
        day = (start_day + timedelta(days=offset)).isoformat()
        count = counted.get(day, 0)
        sale = sale_days.get(day) or {"n": 0, "cents": 0}
        width = 0 if count == 0 or peak == 0 else max(4, round(count * 100 / peak))
        trend.append({
            "day": day,
            "label": day[5:],
            "n": count,
            "width": width,
            "orders": sale["n"],
            "sales": sale["cents"],
        })
    line_key = "orders" if any(point["orders"] for point in trend) else "n"
    chart = _combo_chart(trend, line_key, "sales", money="right", show_line=True)
    chart["line_name"] = "订单数" if line_key == "orders" else "访问"
    chart["bar_name"] = "销售额"
    dist = {
        mode: _combo_chart(_group_trend(trend, mode), "sales", "sales", money="left", show_line=False)
        for mode in ("day", "week", "month")
    }
    bars_only = dist["day"]
    last = trend[-1] if trend else {"n": 0, "orders": 0, "sales": 0}
    prev = trend[-2] if len(trend) > 1 else {"n": 0, "orders": 0, "sales": 0}
    deltas = {
        "orders": _pct(last["orders"], prev["orders"]),
        "sales": _pct(last["sales"], prev["sales"]),
        "visits": _pct(last["n"], prev["n"]),
    }
    items = []
    for row in conn.execute(
        """
        select sku,
               sum(case when kind = 'product' then 1 else 0 end) as views,
               sum(case when kind = 'cart' then qty else 0 end) as carts,
               sum(case when kind = 'paid' then qty else 0 end) as sold,
               sum(case when kind = 'return' then qty else 0 end) as returned,
               sum(case when kind = 'paid' then cents else 0 end) as cents,
               sum(case when kind = 'return' then cents else 0 end) as back
        from visits
        where day >= ? and sku != '' and kind in ('product', 'cart', 'paid', 'return')
        group by sku
        order by views desc, sold desc, sku asc
        limit 20
        """,
        (start,),
    ).fetchall():
        items.append({
            "sku": row["sku"],
            "views": int(row["views"]),
            "carts": int(row["carts"]),
            "sold": max(0, int(row["sold"]) - int(row["returned"])),
            "cents": int(row["cents"]) - int(row["back"]),
        })
    countries = [
        {"code": row["country"] or "—", "n": int(row["n"])}
        for row in conn.execute(
            """
            select country, count(*) as n from visits
            where kind = 'page' and day >= ?
            group by country
            order by n desc
            limit 12
            """,
            (start,),
        ).fetchall()
    ]
    langs = []
    for row in conn.execute(
        """
        select lang, count(*) as n from visits
        where kind = 'page' and day >= ?
        group by lang
        order by n desc
        """,
        (start,),
    ).fetchall():
        count = int(row["n"])
        langs.append({
            "code": row["lang"] or "",
            "name": LANG_LABEL.get(row["lang"], row["lang"] or "未知"),
            "n": count,
            "share": "0%" if pages == 0 else f"{count * 100 / pages:.0f}%",
        })
    lifetime = {row["status"]: row for row in conn.execute(
        "select status, count(*) as n, coalesce(sum(due_cents), 0) as cents from orders group by status"
    ).fetchall()}

    def life(status):
        row = lifetime.get(status)
        if row is None:
            return 0, 0
        return int(row["n"]), int(row["cents"])

    pending_n, _pending_cents = life("pending")
    paid_n, paid_life = life("paid")
    shipped_n, shipped_life = life("shipped")
    refunded_n, refunded_life = life("refunded")
    cancelled_n, _cancelled_cents = life("cancelled")
    sold = {}
    for row in conn.execute(
        """
        select l.sku as sku, sum(l.qty) as qty, sum(l.price_cents * l.qty) as cents
        from order_lines l
        join orders o on o.id = l.order_id
        where o.status in ('paid', 'shipped')
        group by l.sku
        """
    ).fetchall():
        sku = str(row["sku"]).split("~", 1)[0]
        bucket = sold.setdefault(sku, {"sku": sku, "qty": 0, "cents": 0})
        bucket["qty"] += int(row["qty"])
        bucket["cents"] += int(row["cents"])
    sold_rows = sorted(sold.values(), key=lambda item: (-item["qty"], -item["cents"], item["sku"]))[:20]
    return {
        "days": picked,
        "pages": pages,
        "visitors": visitors,
        "products": products,
        "carts": carts,
        "orders": orders,
        "paid_orders": paid_orders,
        "paid_cents": paid_cents,
        "rate": rate,
        "trend": trend,
        "items": items,
        "countries": countries,
        "langs": langs,
        "life_orders": pending_n + paid_n + shipped_n + refunded_n + cancelled_n,
        "life_paid": paid_n + shipped_n,
        "life_cents": paid_life + shipped_life,
        "life_refunded": refunded_n,
        "life_refunded_cents": refunded_life,
        "sold": sold_rows,
        "gmv_cents": sales_cents,
        "refund_rate": "—" if sales == 0 else f"{refunds * 100 / sales:.2f}%",
        "chart": chart,
        "bars": bars_only,
        "dist": dist,
        "deltas": deltas,
    }
