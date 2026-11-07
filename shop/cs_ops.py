# -*- coding: utf-8 -*-
"""Customer-service ops: agent presence, settings, geo, orders, chat translation."""
from __future__ import annotations

import json
import re
import urllib.request
from typing import Any, Callable, Optional

STATUS_ONLINE = "online"
STATUS_AWAY = "away"
STATUS_BUSY = "busy"  # 挂起
STATUS_OFFLINE = "offline"
AGENT_STATUSES = (STATUS_ONLINE, STATUS_AWAY, STATUS_BUSY, STATUS_OFFLINE)

STATUS_LABELS_ZH = {
    STATUS_ONLINE: "在线",
    STATUS_AWAY: "离开",
    STATUS_BUSY: "挂起",
    STATUS_OFFLINE: "离线",
}


def ensure_cs_ops_tables(conn) -> None:
    conn.execute(
        """
        create table if not exists cs_agent_profile (
            username text primary key,
            display_name text not null default '',
            avatar_url text not null default '',
            title text not null default '',
            can_cs integer not null default 1,
            status text not null default 'offline',
            status_note text not null default '',
            last_seen_at text not null default '',
            updated_at text not null default ''
        )
        """
    )
    conn.execute(
        """
        create table if not exists cs_settings (
            key text primary key,
            value text not null default ''
        )
        """
    )
    conn.execute(
        """
        create table if not exists cs_stickers (
            id integer primary key,
            pack text not null default '常用',
            label text not null default '',
            emoji text not null default '',
            image_url text not null default '',
            enabled integer not null default 1,
            sort_n integer not null default 0
        )
        """
    )
    conn.execute(
        """
        create table if not exists cs_canned (
            id integer primary key,
            category text not null default '通用',
            title text not null,
            body_zh text not null,
            enabled integer not null default 1,
            sort_n integer not null default 0
        )
        """
    )
    # soft columns on cs_rooms
    cols = {r["name"] for r in conn.execute("pragma table_info(cs_rooms)").fetchall()}
    alters = {
        "client_ip": "text not null default ''",
        "geo_country": "text not null default ''",
        "geo_region": "text not null default ''",
        "geo_city": "text not null default ''",
        "user_lang": "text not null default ''",
        "assignee": "text not null default ''",
        "prev_assignee": "text not null default ''",
        "ai_mode": "integer not null default 0",
        "tags_json": "text not null default '[]'",
        "cart_json": "text not null default '[]'",
    }
    for name, decl in alters.items():
        if name not in cols:
            conn.execute(f"alter table cs_rooms add column {name} {decl}")
    msg_cols = {r["name"] for r in conn.execute("pragma table_info(cs_messages)").fetchall()}
    msg_alters = {
        "body_original": "text not null default ''",
        "body_zh": "text not null default ''",
        "lang": "text not null default ''",
        "translated": "integer not null default 0",
    }
    for name, decl in msg_alters.items():
        if name not in msg_cols:
            conn.execute(f"alter table cs_messages add column {name} {decl}")
    # seed settings
    defaults = {
        "translate_enabled": "1",
        "show_ip_geo": "1",
        "show_orders": "1",
        "require_cs_account": "1",
        "default_agent_status": STATUS_ONLINE,
        "ai_enabled": "1",
        "ai_only_when_offline": "0",
        "ai_name": "Harbor",
        "ai_persona": "你是 Harbor 跨境店铺客服（对外就叫 Harbor），语气礼貌、短、具体，像认真的店员，不是朋友闲聊。\n\n进线后按上下文回答，不要编造：\n1) 有订单就处理发货和物流问题，不催下单。\n2) 购物车里有商品就只谈这些商品。\n3) 没有购物车就只谈顾客正在看的商品。\n4) 用顾客这条消息的语言回答。\n\n硬规则：\n- 禁止玩笑、嘲讽、哈哈、呵呵、笑呢、讥讽，也不要接顾客的玩笑。\n- 未下单只说「下单后尽快安排发出」。禁止说已经在路上。\n- 每次只回 1 句。禁止自称 AI。",
        "ai_handoff_keywords": "人工,转人工,客服,agent,human,refund,退款,投诉",
        "assign_only_mine": "1",
        "auto_reassign_when_away": "1",
    }
    for k, v in defaults.items():
        row = conn.execute("select key from cs_settings where key=?", (k,)).fetchone()
        if not row:
            conn.execute("insert into cs_settings (key, value) values (?, ?)", (k, v))
    if conn.execute("select count(*) as n from cs_canned").fetchone()["n"] == 0:
        seeds = [
            ("售前", "商品咨询", "您好，请问想了解这款商品的哪方面？尺寸、材质还是用法？"),
            ("物流", "查物流", "请提供订单号，我帮您查询物流进度。"),
            ("售后", "退换说明", "抱歉给您带来不便。请说明问题并尽量附上照片，我们会尽快处理。"),
            ("通用", "稍等", "好的，请稍等，我马上为您核实。"),
        ]
        for i, (cat, title, body) in enumerate(seeds):
            conn.execute(
                "insert into cs_canned (category, title, body_zh, enabled, sort_n) values (?,?,?,1,?)",
                (cat, title, body, i),
            )


    if conn.execute("select count(*) as n from cs_stickers").fetchone()["n"] == 0:
        sticker_seeds = [
            ("常用", "比心", "🥰", "", 0),
            ("常用", "好的", "👍", "", 1),
            ("常用", "哈哈", "😄", "", 2),
            ("常用", "谢谢", "🙏", "", 3),
            ("常用", "稍等", "⏳", "", 4),
            ("常用", "惊喜", "✨", "", 5),
            ("常用", "爱心", "❤️", "", 6),
            ("常用", "抱抱", "🤗", "", 7),
            ("购物", "喜欢", "😍", "", 8),
            ("购物", "下单", "🛒", "", 9),
            ("购物", "礼盒", "🎁", "", 10),
            ("购物", "火箭", "🚀", "", 11),
        ]
        for pack, label, emoji, img, sort_n in sticker_seeds:
            conn.execute(
                "insert into cs_stickers (pack, label, emoji, image_url, enabled, sort_n) values (?,?,?,?,1,?)",
                (pack, label, emoji, img, sort_n),
            )

def get_setting(conn, key: str, default: str = "") -> str:
    row = conn.execute("select value from cs_settings where key=?", (key,)).fetchone()
    return str(row["value"]) if row else default


def set_setting(conn, key: str, value: str) -> None:
    conn.execute(
        "insert into cs_settings (key, value) values (?, ?) on conflict(key) do update set value=excluded.value",
        (key, str(value)),
    )


def all_settings(conn) -> dict:
    rows = conn.execute("select key, value from cs_settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


def ensure_agent_profile(conn, username: str) -> None:
    ensure_cs_ops_tables(conn)
    row = conn.execute("select username from cs_agent_profile where username=?", (username,)).fetchone()
    if not row:
        conn.execute(
            "insert into cs_agent_profile (username, display_name, can_cs, status) values (?, ?, 1, ?)",
            (username, username, STATUS_OFFLINE),
        )


def agent_dict(conn, username: str) -> dict:
    ensure_agent_profile(conn, username)
    row = conn.execute("select * from cs_agent_profile where username=?", (username,)).fetchone()
    staff = conn.execute("select username, role, enabled from staff where username=?", (username,)).fetchone()
    return {
        "username": username,
        "display_name": row["display_name"] or username,
        "avatar_url": row["avatar_url"] or "",
        "title": row["title"] or "",
        "can_cs": int(row["can_cs"] or 0),
        "status": row["status"] or STATUS_OFFLINE,
        "status_label": STATUS_LABELS_ZH.get(row["status"] or STATUS_OFFLINE, row["status"]),
        "status_note": row["status_note"] or "",
        "last_seen_at": row["last_seen_at"] or "",
        "role": (staff["role"] if staff else ""),
        "enabled": int(staff["enabled"]) if staff else 0,
    }


def list_cs_agents(conn) -> list:
    ensure_cs_ops_tables(conn)
    # sync profiles for all staff
    for s in conn.execute("select username from staff").fetchall():
        ensure_agent_profile(conn, s["username"])
    rows = conn.execute(
        """
        select p.*, s.role, s.enabled
        from cs_agent_profile p
        join staff s on s.username = p.username
        where p.can_cs = 1
        order by s.enabled desc, p.display_name, p.username
        """
    ).fetchall()
    out = []
    for row in rows:
        out.append(
            {
                "username": row["username"],
                "display_name": row["display_name"] or row["username"],
                "avatar_url": row["avatar_url"] or "",
                "title": row["title"] or "",
                "can_cs": int(row["can_cs"] or 0),
                "status": row["status"] or STATUS_OFFLINE,
                "status_label": STATUS_LABELS_ZH.get(row["status"] or STATUS_OFFLINE, ""),
                "status_note": row["status_note"] or "",
                "last_seen_at": row["last_seen_at"] or "",
                "role": row["role"],
                "enabled": int(row["enabled"] or 0),
            }
        )
    return out


def set_agent_status(conn, username: str, status: str, note: str = "", now: str = "") -> dict:
    ensure_agent_profile(conn, username)
    if status not in AGENT_STATUSES:
        status = STATUS_ONLINE
    conn.execute(
        """
        update cs_agent_profile
        set status=?, status_note=?, last_seen_at=?, updated_at=?
        where username=?
        """,
        (status, (note or "")[:120], now, now, username),
    )
    return agent_dict(conn, username)


def update_agent_profile(conn, username: str, *, display_name: str = None, title: str = None, avatar_url: str = None, can_cs: int = None) -> dict:
    ensure_agent_profile(conn, username)
    row = agent_dict(conn, username)
    dn = display_name if display_name is not None else row["display_name"]
    ti = title if title is not None else row["title"]
    av = avatar_url if avatar_url is not None else row["avatar_url"]
    cc = can_cs if can_cs is not None else row["can_cs"]
    conn.execute(
        "update cs_agent_profile set display_name=?, title=?, avatar_url=?, can_cs=? where username=?",
        ((dn or "")[:64], (ti or "")[:64], (av or "")[:300], 1 if cc else 0, username),
    )
    return agent_dict(conn, username)


def client_ip_from_request(request) -> str:
    # honor common proxy headers; first public-looking hop
    xff = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if xff:
        return xff[:64]
    xri = (request.headers.get("x-real-ip") or "").strip()
    if xri:
        return xri[:64]
    try:
        return (request.client.host if request.client else "")[:64]
    except Exception:
        return ""


def lookup_geo(ip: str) -> dict:
    """Best-effort free geo. Fail soft."""
    ip = (ip or "").strip()
    empty = {"country": "", "region": "", "city": "", "label": ""}
    if not ip or ip.startswith("127.") or ip.startswith("10.") or ip.startswith("192.168.") or ip == "::1":
        return {**empty, "label": "本地/内网"}
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city&lang=zh-CN"
        with urllib.request.urlopen(url, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        if data.get("status") != "success":
            return empty
        country = data.get("country") or ""
        region = data.get("regionName") or ""
        city = data.get("city") or ""
        parts = [p for p in (country, region, city) if p]
        return {"country": country, "region": region, "city": city, "label": " / ".join(parts)}
    except Exception:
        return empty


_LANG_HINTS = [
    ("zh", re.compile(r"[\u4e00-\u9fff]")),
    ("ja", re.compile(r"[\u3040-\u30ff]")),
    ("ko", re.compile(r"[\uac00-\ud7af]")),
    ("ru", re.compile(r"[А-Яа-яЁё]")),
    ("ar", re.compile(r"[\u0600-\u06ff]")),
    ("de", re.compile(r"\b(der|die|das|und|nicht|ich|sie)\b", re.I)),
    ("fr", re.compile(r"\b(je|vous|bonjour|merci|pas|une|les)\b", re.I)),
    ("es", re.compile(r"\b(hola|gracias|por|que|una|los|las)\b", re.I)),
    ("pt", re.compile(r"\b(obrigad|você|não|uma|para)\b", re.I)),
    ("en", re.compile(r"\b(the|and|you|please|order|shipping|hello|thanks)\b", re.I)),
]


def detect_lang(text: str, fallback: str = "en") -> str:
    s = (text or "").strip()
    if not s:
        return fallback
    for code, rx in _LANG_HINTS:
        if rx.search(s):
            return code
    # latin default english
    if re.search(r"[A-Za-z]", s):
        return "en"
    return fallback


def map_deepl_lang(code: str) -> str:
    c = (code or "en").lower()
    if c.startswith("zh"):
        return "zh"
    if c in {"en", "es", "de", "fr", "pt", "ja", "ko", "ru", "ar", "it", "nl", "pl", "tr"}:
        return c
    return "en"


def translate_text(translate: Optional[Callable], text: str, source: str, target: str) -> str:
    if not text:
        return ""
    if not translate:
        return text
    src = map_deepl_lang(source)
    tgt = map_deepl_lang(target)
    if src == tgt:
        return text
    try:
        return translate(text, src, tgt)
    except Exception:
        try:
            # many translators want en as pivot
            if src != "en" and tgt != "en":
                mid = translate(text, src, "en")
                return translate(mid, "en", tgt)
        except Exception:
            return text
        return text


def prepare_user_message(translate, body: str, room_lang: str, translate_enabled: bool) -> dict:
    """User wrote in their language -> store original + zh for staff."""
    lang = detect_lang(body, fallback=room_lang or "en")
    body_zh = body
    translated = 0
    if translate_enabled and lang != "zh":
        body_zh = translate_text(translate, body, lang, "zh")
        translated = 1 if body_zh and body_zh != body else 0
    return {
        "body_store": body_zh if translated else body,  # primary body shown to staff = zh when possible
        "body_original": body,
        "body_zh": body_zh,
        "lang": lang,
        "translated": translated,
    }


def prepare_staff_message(translate, body_zh: str, user_lang: str, translate_enabled: bool) -> dict:
    """Staff writes Chinese -> user sees user_lang."""
    lang = map_deepl_lang(user_lang or "en")
    body_user = body_zh
    translated = 0
    if translate_enabled and lang != "zh":
        body_user = translate_text(translate, body_zh, "zh", lang)
        translated = 1 if body_user and body_user != body_zh else 0
    return {
        "body_store": body_zh,  # staff side keeps zh as body
        "body_original": body_zh,
        "body_zh": body_zh,
        "body_user": body_user,
        "lang": lang,
        "translated": translated,
    }


def orders_for_email(conn, email: str, limit: int = 20) -> list:
    email = (email or "").strip().lower()
    if not email:
        return []
    try:
        rows = conn.execute(
            """
            select id, submit_id, email, status, currency, due_cents, due_local,
                   ship_country, ship_name, address, city, region, postal, phone,
                   tracking, carrier, shipped_at, created_at, updated_at
            from orders
            where lower(email)=?
            order by id desc
            limit ?
            """,
            (email, limit),
        ).fetchall()
    except Exception:
        # tracking columns may not exist
        rows = conn.execute(
            """
            select id, submit_id, email, status, currency, due_cents, due_local,
                   ship_country, ship_name, address, city, region, postal, phone, created_at
            from orders
            where lower(email)=?
            order by id desc
            limit ?
            """,
            (email, limit),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        out.append(
            {
                "id": d.get("id"),
                "submit_id": d.get("submit_id") or "",
                "email": d.get("email") or "",
                "status": d.get("status") or "",
                "currency": d.get("currency") or "",
                "due_cents": int(d.get("due_cents") or 0),
                "ship_country": d.get("ship_country") or "",
                "ship_name": d.get("ship_name") or "",
                "address": d.get("address") or "",
                "city": d.get("city") or "",
                "region": d.get("region") or "",
                "postal": d.get("postal") or "",
                "phone": d.get("phone") or "",
                "tracking": d.get("tracking") or "",
                "carrier": d.get("carrier") or "",
                "shipped_at": d.get("shipped_at") or "",
                "created_at": d.get("created_at") or "",
            }
        )
    return out


def order_detail(conn, order_id: int) -> Optional[dict]:
    row = conn.execute("select * from orders where id=?", (order_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        lines = conn.execute(
            "select * from order_lines where order_id=? order by id",
            (order_id,),
        ).fetchall()
        d["lines"] = [dict(x) for x in lines]
    except Exception:
        d["lines"] = []
    return d



ACTIVE_ORDER_STATUSES = {"pending", "paid", "shipped"}


def _order_line_titles(conn, order_id: int, limit: int = 3) -> list:
    titles = []
    try:
        rows = conn.execute(
            """
            select ol.sku, ol.qty, ifnull(p.names,'') as names, ifnull(p.source_zh,'') as source_zh
            from order_lines ol
            left join products p on p.sku = ol.sku
            where ol.order_id=?
            order by ol.rowid
            limit ?
            """,
            (order_id, limit),
        ).fetchall()
    except Exception:
        try:
            rows = conn.execute(
                "select sku, qty from order_lines where order_id=? order by rowid limit ?",
                (order_id, limit),
            ).fetchall()
        except Exception:
            return titles
    for r in rows:
        d = dict(r)
        name = ""
        names = d.get("names") or ""
        if names:
            try:
                parsed = json.loads(names) if isinstance(names, str) and names.strip().startswith("{") else None
                if isinstance(parsed, dict):
                    name = str(parsed.get("en") or parsed.get("zh") or next(iter(parsed.values()), "") or "")
                else:
                    name = str(names)[:80]
            except Exception:
                name = str(names)[:80]
        if not name:
            name = (d.get("source_zh") or d.get("sku") or "").strip()
        qty = int(d.get("qty") or 1)
        bit = name or str(d.get("sku") or "")
        if qty > 1 and bit:
            bit = f"{bit} x{qty}"
        if bit:
            titles.append(bit)
    return titles


def order_context_for_room(conn, room: dict | None, limit: int = 5) -> dict:
    """Reuse email matching like /admin/support/api/orders. Empty email => no orders."""
    room = dict(room or {})
    email = (room.get("email") or "").strip().lower()
    orders = orders_for_email(conn, email, limit=limit) if email else []
    active = [o for o in orders if (o.get("status") or "").lower() in ACTIVE_ORDER_STATUSES]
    pick = active[0] if active else (orders[0] if orders else None)
    if not pick:
        return {
            "order_status": "none",
            "has_order": False,
            "email": email,
            "orders": [],
            "summary": "order_status: none (customer has not placed an order)",
        }
    status = (pick.get("status") or "").lower() or "unknown"
    enriched = []
    for o in orders[:limit]:
        oid = o.get("id")
        items = _order_line_titles(conn, int(oid)) if oid is not None else []
        enriched.append(
            {
                "id": oid,
                "status": (o.get("status") or ""),
                "tracking": (o.get("tracking") or ""),
                "carrier": (o.get("carrier") or ""),
                "created_at": (o.get("created_at") or ""),
                "items": items,
            }
        )
    lines = []
    for e in enriched[:3]:
        item_s = ", ".join(e["items"]) if e["items"] else "(items n/a)"
        track = e["tracking"] if e["tracking"] else ""
        bit = f"#{e['id']} status={e['status']} items={item_s}"
        if track:
            bit += f" tracking={track}"
        lines.append(bit)
    has_order = status in ACTIVE_ORDER_STATUSES
    summary = (
        f"order_status: {status if has_order else (status or 'none')}; "
        f"has_active_order: {'yes' if has_order else 'no'}; "
        f"latest: " + ("; ".join(lines) if lines else "(none)")
    )
    if not has_order:
        # cancelled/refunded only — treat speech rules closer to none for shipping claims
        summary = f"order_status: {status}; has_active_order: no; latest: " + ("; ".join(lines) if lines else "(none)")
    return {
        "order_status": status if pick else "none",
        "has_order": has_order,
        "email": email,
        "orders": enriched,
        "summary": summary,
    }


def list_canned(conn, enabled_only: bool = False) -> list:
    ensure_cs_ops_tables(conn)
    q = "select * from cs_canned"
    if enabled_only:
        q += " where enabled=1"
    q += " order by sort_n, id"
    return [dict(r) for r in conn.execute(q).fetchall()]


def list_stickers(conn, enabled_only: bool = True) -> list:
    ensure_cs_ops_tables(conn)
    sql = "select * from cs_stickers"
    if enabled_only:
        sql += " where enabled=1"
    sql += " order by sort_n asc, id asc"
    rows = conn.execute(sql).fetchall()
    return [
        {
            "id": int(r["id"]),
            "pack": r["pack"],
            "label": r["label"],
            "emoji": r["emoji"],
            "image_url": r["image_url"] or "",
        }
        for r in rows
    ]


def wants_human_handoff(text: str, keywords: str) -> bool:
    raw = (text or "").lower()
    for part in (keywords or "").split(","):
        k = part.strip().lower()
        if k and k in raw:
            return True
    return False


def any_agent_online(conn) -> bool:
    ensure_cs_ops_tables(conn)
    row = conn.execute(
        "select count(*) as n from cs_agent_profile where can_cs=1 and status=?",
        (STATUS_ONLINE,),
    ).fetchone()
    return int(row["n"] or 0) > 0




def is_latin_heavy(text: str) -> bool:
    s = str(text or "")
    if not s.strip():
        return True
    letters = sum(1 for ch in s if ("A" <= ch <= "Z") or ("a" <= ch <= "z"))
    cjk = sum(1 for ch in s if "\u4e00" <= ch <= "\u9fff" or "\u3040" <= ch <= "\u30ff" or "\uac00" <= ch <= "\ud7af")
    if cjk > 0 and cjk >= letters:
        return False
    return letters >= max(1, cjk)


def typing_delay_seconds(text: str) -> float:
    """Human-ish typing pace: ~3 chars/s for CJK-heavy, ~14 chars/s for Latin-heavy."""
    n = max(1, len(str(text or "").strip()))
    if is_latin_heavy(text):
        delay = float(n) / 14.0
    else:
        delay = float(n) / 3.0
    return max(1.0, min(35.0, delay))


def split_cs_ai_bubbles(text: str) -> list:
    """Split long AI reply into short chat bubbles."""
    raw = (text or "").strip()
    if not raw:
        return []
    chunks = []
    for part in re.split(r"[\n\r]+", raw):
        part = part.strip()
        if part:
            chunks.append(part)
    if not chunks:
        chunks = [raw]

    def _sent_split(s: str) -> list:
        s = s.strip()
        if not s:
            return []
        latin = is_latin_heavy(s)
        if latin:
            parts = re.split(r"(?<=[.!?])\s+", s)
        else:
            parts = re.split(r"(?<=[。！？!?])\s*", s)
        out = [p.strip() for p in parts if p and p.strip()]
        return out or [s]

    expanded = []
    for c in chunks:
        limit_soft = 120 if is_latin_heavy(c) else 40
        if len(c) > limit_soft or ("。" in c or ". " in c or "！" in c or "？" in c or "?" in c or "!" in c):
            pieces = _sent_split(c)
            if len(pieces) > 1:
                expanded.extend(pieces)
            else:
                expanded.append(c)
        else:
            expanded.append(c)

    final = []
    for c in expanded:
        limit = 120 if is_latin_heavy(c) else 40
        if len(c) <= limit:
            final.append(c)
            continue
        if is_latin_heavy(c):
            cur = ""
            for w in re.split(r"(\s+)", c):
                if len(cur) + len(w) > limit and cur.strip():
                    final.append(cur.strip())
                    cur = w.lstrip()
                else:
                    cur += w
            if cur.strip():
                final.append(cur.strip())
        else:
            for i in range(0, len(c), limit):
                piece = c[i : i + limit].strip()
                if piece:
                    final.append(piece)
    return final[:4]



def _product_display_name(conn, sku: str) -> str:
    sku = (sku or "").split("~", 1)[0].strip()
    if not sku:
        return ""
    try:
        row = conn.execute(
            "select names, source_zh from products where sku=?",
            (sku,),
        ).fetchone()
    except Exception:
        return sku
    if not row:
        return sku
    name = ""
    names = row["names"] if "names" in row.keys() else ""
    if names:
        try:
            parsed = json.loads(names) if isinstance(names, str) and str(names).strip().startswith("{") else None
            if isinstance(parsed, dict):
                name = str(parsed.get("en") or parsed.get("zh") or next(iter(parsed.values()), "") or "")
            else:
                name = str(names)[:80]
        except Exception:
            name = str(names)[:80]
    if not name:
        try:
            name = (row["source_zh"] if "source_zh" in row.keys() else "") or ""
        except Exception:
            name = ""
    return (name or sku).strip()


def normalize_cart_lines(raw) -> list:
    """Accept cookie string, list of dicts, or JSON string -> [{sku,name,qty}]."""
    items = raw
    if raw is None:
        return []
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return []
        if s.startswith("[") or s.startswith("{"):
            try:
                items = json.loads(s)
            except Exception:
                items = s
        else:
            # cookie format sku:qty,sku:qty
            out = []
            for part in s.split(","):
                if ":" not in part:
                    continue
                sku, qty = part.split(":", 1)
                try:
                    q = int(qty)
                except Exception:
                    continue
                sku = sku.strip()
                if sku and q > 0:
                    out.append({"sku": sku, "qty": q, "name": ""})
            return out
    if isinstance(items, dict):
        items = items.get("lines") or items.get("items") or items.get("cart") or []
    if not isinstance(items, list):
        return []
    out = []
    for it in items[:20]:
        if not isinstance(it, dict):
            continue
        sku = str(it.get("sku") or it.get("code") or it.get("productSku") or "").strip()
        if not sku:
            continue
        try:
            qty = int(it.get("qty") or it.get("quantity") or 1)
        except Exception:
            qty = 1
        if qty <= 0:
            continue
        name = str(it.get("name") or it.get("title") or "").strip()[:120]
        out.append({"sku": sku, "name": name, "qty": qty})
    return out


def cart_context_for_room(conn, room: dict | None, cart_raw=None) -> dict:
    """Cart is browser cookie `cart` (sku:qty,...) and/or H5 payload; snapshotted on cs_rooms.cart_json.
    There is no server cart table keyed by email — never invent lines.
    """
    room = dict(room or {})
    lines = normalize_cart_lines(cart_raw)
    if not lines:
        lines = normalize_cart_lines(room.get("cart") or room.get("cart_json") or "")
    if not lines:
        return {
            "has_cart": False,
            "lines": [],
            "summary": "Cart: none",
        }
    enriched = []
    bits = []
    for ln in lines:
        sku = ln.get("sku") or ""
        name = (ln.get("name") or "").strip() or _product_display_name(conn, sku)
        qty = int(ln.get("qty") or 1)
        enriched.append({"sku": sku, "name": name, "qty": qty})
        bit = name or sku
        if qty > 1:
            bit = f"{bit} x{qty}"
        bits.append(f"{bit} ({sku})" if sku and name else bit)
    return {
        "has_cart": True,
        "lines": enriched,
        "summary": "Cart: " + "; ".join(bits),
    }


def browse_summary_for_room(room: dict | None, conn=None) -> str:
    room = dict(room or {})
    cur = room.get("current") or {}
    hist = room.get("history") or []
    lines = []
    csku = str(cur.get("sku") or "").strip()
    cname = str(cur.get("name") or "").strip()
    if csku or cname:
        lines.append(
            "Current viewing: "
            + (cname or "-")
            + " | SKU "
            + (csku or "-")
            + " | price "
            + str(cur.get("price") or "-")
        )
    seen = set()
    if csku:
        seen.add(csku)
    for it in (hist or [])[:8]:
        if not isinstance(it, dict):
            continue
        sku = str(it.get("sku") or "").strip()
        if not sku or sku in seen:
            continue
        seen.add(sku)
        lines.append(
            "- "
            + str(it.get("name") or sku)
            + (" " + str(it.get("price") or "")).rstrip()
        )
    # optional visits fallback by visitor_id
    if conn is not None and len(lines) <= 1:
        vid = str(room.get("visitor_id") or "").strip()
        if vid:
            try:
                rows = conn.execute(
                    """
                    select sku from visits
                    where visitor=? and kind='product' and ifnull(sku,'')!=''
                    order by id desc limit 8
                    """,
                    (vid,),
                ).fetchall()
            except Exception:
                rows = []
            for r in rows:
                sku = str(r["sku"] if hasattr(r, "keys") else r[0] or "").strip()
                if not sku or sku in seen:
                    continue
                seen.add(sku)
                name = _product_display_name(conn, sku) if conn is not None else sku
                lines.append("- " + (name or sku))
    if not lines:
        return "Browse: none"
    return "Browse:\n" + "\n".join(lines)


def locale_habit_hint(lang: str, geo: dict | None = None) -> str:
    lang = (lang or "en").lower()
    geo = dict(geo or {})
    country = str(geo.get("country") or "").upper()
    label = str(geo.get("label") or "")
    bits = [f"lang={lang}"]
    if country:
        bits.append(f"country={country}")
    if label:
        bits.append(f"geo={label}")
    base = "Locale: " + ", ".join(bits) + ". "
    if lang.startswith("zh"):
        habit = "简体中文店员口吻：礼貌、短、具体。禁止玩笑、嘲讽、哈哈、呵呵。"
    elif lang.startswith("es"):
        habit = "Spanish chat: warmer, friendly short lines; light emoji ok; still a store CS."
    elif lang.startswith("pt"):
        habit = "Portuguese: warm, casual short lines; still professional CS."
    elif lang.startswith("fr"):
        habit = "French: polite but casual short lines, not stiff formal letter tone."
    elif lang.startswith("de"):
        habit = "German: clear, friendly, concise; not overly formal."
    elif lang.startswith("ja"):
        habit = "Japanese: polite soft short lines, natural CS tone."
    elif lang.startswith("ko"):
        habit = "Korean: friendly polite short lines."
    else:
        # English + US/UK/AU nuances
        if country in {"US", "CA"} or "United States" in label:
            habit = "English store clerk: polite, short, concrete. No jokes."
        elif country in {"GB", "UK", "AU", "NZ"}:
            habit = "English store clerk: polite, short, concrete. No jokes."
        else:
            habit = "Store clerk: polite, short, concrete. No jokes or sarcasm."
    return base + "Habit: " + habit



def build_cs_ai_prompt(
    room: dict,
    recent_msgs: list,
    persona: str,
    ai_name: str,
    user_text: str,
    order_ctx: dict | None = None,
    cart_ctx: dict | None = None,
) -> str:
    room = dict(room or {})
    cur = room.get("current") or {}
    hist = room.get("history") or []
    chat_lines = []
    for m in (recent_msgs or [])[-12:]:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        body = str(
            m.get("body_user_original")
            or m.get("body_original")
            or m.get("body")
            or ""
        )
        if body.startswith("[ops]"):
            continue
        if role == "staff":
            who = "Agent (coworker, not the customer)"
        elif role == "user":
            who = "User"
        else:
            who = "System"
        if body.startswith("[product]") or body.startswith("[cart]"):
            body = who + " sent a product or cart card"
            chat_lines.append(body)
            continue
        chat_lines.append(who + ": " + body)
    detected = detect_lang(user_text, fallback=(room.get("user_lang") or "en"))
    lang = detected or room.get("user_lang") or "en"
    order_ctx = dict(order_ctx or {})
    cart_ctx = dict(cart_ctx or {})
    if not cart_ctx:
        cart_ctx = {"summary": "Cart: none", "has_cart": False, "lines": []}
    ostatus = (order_ctx.get("order_status") or "none").lower()
    has_order = bool(order_ctx.get("has_order"))
    has_cart = bool(cart_ctx.get("has_cart"))
    geo = room.get("geo") if isinstance(room.get("geo"), dict) else {
        "country": room.get("geo_country") or "",
        "region": room.get("geo_region") or "",
        "city": room.get("geo_city") or "",
        "label": room.get("geo_label") or "",
    }
    ip = str(room.get("client_ip") or "")
    habit = locale_habit_hint(lang, geo)
    browse = browse_summary_for_room(room)
    # keep browse_summary_for_room(conn=) optional — room history already set
    if has_order:
        order_rule = (
            "STEP1 ORDER: ALREADY ordered (status="
            + ostatus
            + "). Returning-customer tone. Reassure processing/shipping/in-transit. "
            "Do NOT push place-order. Do NOT invent tracking. Vague cross-border ASAP only."
        )
        sales_rule = "STEP2/3: With an active order, do not hard-sell cart/browse items; answer service questions."
    else:
        order_rule = (
            "STEP1 ORDER: NO active order (order_status="
            + ostatus
            + "). New-buyer pre-sales. Soft-close when relevant. "
            "If asked arrival/shipping: AFTER they order we arrange ASAP and it arrives ASAP. "
            "FORBIDDEN: claiming already shipping / in motion / on its way as if ordered."
        )
        if has_cart:
            sales_rule = (
                "STEP2 CART first: name the cart item and talk specs/benefits briefly, then soft nudge checkout. "
                "STEP3 BROWSE: use current/recent views as backup context."
            )
        else:
            sales_rule = (
                "STEP2 CART: none/unknown — do not invent a cart. "
                "STEP3 BROWSE: focus on current product / recent views; soft nudge to order that item."
            )
    parts = [
        persona.strip(),
        "",
        "Your display name is " + str(ai_name) + ".",
        "Must reply in language code: " + str(lang) + " ONLY (same as latest user message).",
        habit,
        "IP: " + (ip or "(unknown)"),
        "Order context: " + str(order_ctx.get("summary") or "order_status: none"),
        order_rule,
        str(cart_ctx.get("summary") or "Cart: none"),
        sales_rule,
        browse,
        "",
        "Recent chat:",
        ("\n".join(chat_lines) if chat_lines else "(none)"),
        "",
        "Latest user message: " + str(user_text),
        "Only the Latest user message is the customer. Lines marked Agent are the human coworker. Never treat the coworker's words as the customer's, and never answer the coworker.",
        "Write ONLY the customer-facing reply.",
        "ONE short polite sentence. No emoji. No AI self-intro.",
        "FORBIDDEN tone: jokes, sarcasm, teasing, 哈哈, 呵呵, 笑, lol, lmao. If the customer jokes, ignore the joke and answer the order question.",
        "Name the product once, plainly. Do not comment on the customer's attitude.",
        "Never say already shipping / in motion / on its way as if the parcel already left.",
    ]
    return "\n".join(parts)


def generate_cs_ai_reply(complete, room: dict, recent_msgs: list, *, persona: str, ai_name: str, user_text: str, order_ctx: dict | None = None, cart_ctx: dict | None = None) -> str:
    """Return reply text or empty."""
    room = dict(room or {})
    room["user_lang"] = detect_lang(user_text, fallback=(room.get("user_lang") or "en"))
    order_ctx = dict(order_ctx or {})
    cart_ctx = dict(cart_ctx or {})
    has_order = bool(order_ctx.get("has_order"))
    def _fallback() -> str:
        name = (room.get("current") or {}).get("name") or "this item"
        lang = (room.get("user_lang") or "en").lower()
        if has_order:
            if lang.startswith("zh"):
                return "你的订单我们这边已经在跟了，会尽快安排发出，物流也会尽快送到～"
            if lang.startswith("es"):
                return "Tu pedido ya está en proceso — lo enviamos lo antes posible 🌍"
            return "Your order is already in process — we'll ship it out ASAP 🌍"
        if lang.startswith("zh"):
            return "「" + str(name) + "」下单后我们会尽快安排发出。需要的话我可以帮你确认规格。"
        if lang.startswith("es"):
            return "¡Claro! Con «" + str(name) + "», tras pedir enviamos lo antes posible — ¿lo dejamos listo?"
        return "Once you order «" + str(name) + "», we arrange shipment as soon as we can. I can confirm the option if you need."

    if not complete:
        return _fallback()
    try:
        # normalize message list (reject bare strings)
        if isinstance(recent_msgs, str):
            recent_msgs = []
        elif not isinstance(recent_msgs, list):
            recent_msgs = list(recent_msgs or [])
        recent_msgs = [m for m in recent_msgs if isinstance(m, dict)]
        prompt = build_cs_ai_prompt(room, recent_msgs, persona, ai_name, user_text, order_ctx=order_ctx, cart_ctx=cart_ctx)
        try:
            out = complete(prompt, max_tokens=100)
        except TypeError:
            out = complete(prompt)
        text = (out or "").strip()[:280]
        if cs_tone_blocked(text):
            return _fallback()
        return text or _fallback()
    except Exception:
        return _fallback()


UNAVAILABLE_STATUSES = {STATUS_AWAY, STATUS_BUSY, STATUS_OFFLINE}


def is_agent_unavailable(status: str) -> bool:
    return (status or STATUS_OFFLINE) in UNAVAILABLE_STATUSES


def staff_is_admin(conn, username: str) -> bool:
    row = conn.execute("select role from staff where username=?", (username,)).fetchone()
    if not row:
        return False
    role = (row["role"] or "").strip().lower()
    return role in {"admin", "owner", "superadmin"}


def room_visible_to_agent(conn, room_row_or_dict, username: str) -> bool:
    """Admin always sees all; others see own + unassigned when assign_only_mine is on."""
    ensure_cs_ops_tables(conn)
    if staff_is_admin(conn, username):
        return True
    if get_setting(conn, "assign_only_mine", "1") != "1":
        return True
    if isinstance(room_row_or_dict, dict):
        assignee = (room_row_or_dict.get("assignee") or "").strip()
    else:
        try:
            assignee = (room_row_or_dict["assignee"] if "assignee" in room_row_or_dict.keys() else "") or ""
        except Exception:
            assignee = ""
        assignee = str(assignee).strip()
    return assignee == "" or assignee == username


def filter_rooms_for_agent(conn, rooms: list, username: str) -> list:
    return [r for r in rooms if room_visible_to_agent(conn, r, username)]


def set_room_assignee(conn, room_id: str, username: str, *, prev: str = None) -> None:
    ensure_cs_ops_tables(conn)
    row = conn.execute("select assignee, prev_assignee from cs_rooms where id=?", (room_id,)).fetchone()
    if row is None:
        return
    cur = (row["assignee"] or "").strip()
    new_u = (username or "").strip()
    if prev is None:
        prev_val = cur if cur and cur != new_u else (row["prev_assignee"] or "")
    else:
        prev_val = (prev or "").strip()
    cols = {r["name"] for r in conn.execute("pragma table_info(cs_rooms)").fetchall()}
    if "prev_assignee" in cols:
        conn.execute(
            "update cs_rooms set assignee=?, prev_assignee=? where id=?",
            (new_u, prev_val, room_id),
        )
    else:
        conn.execute("update cs_rooms set assignee=? where id=?", (new_u, room_id))


def claim_room_if_unassigned(conn, room_id: str, username: str) -> bool:
    """First human reply claims an unassigned room. Returns True if claimed now."""
    ensure_cs_ops_tables(conn)
    row = conn.execute("select assignee from cs_rooms where id=?", (room_id,)).fetchone()
    if row is None:
        return False
    cur = (row["assignee"] or "").strip()
    if cur:
        return False
    set_room_assignee(conn, room_id, username, prev="")
    return True


def online_cs_agents(conn, *, exclude: str = "") -> list:
    """Enabled staff with can_cs=1 and status=online."""
    agents = list_cs_agents(conn)
    out = []
    for a in agents:
        if not a.get("enabled"):
            continue
        if not a.get("can_cs"):
            continue
        if (a.get("status") or "") != STATUS_ONLINE:
            continue
        if exclude and a.get("username") == exclude:
            continue
        out.append(a)
    return out


def pick_online_agent(conn, *, exclude: str = "") -> Optional[dict]:
    """Round-robin-ish: least open assigned rooms, then username."""
    cands = online_cs_agents(conn, exclude=exclude)
    if not cands:
        return None
    counts = {}
    for r in conn.execute(
        "select assignee, count(*) as n from cs_rooms where status='open' and assignee!='' group by assignee"
    ).fetchall():
        counts[r["assignee"]] = int(r["n"] or 0)
    cands.sort(key=lambda a: (counts.get(a["username"], 0), a.get("username") or ""))
    return cands[0]


def display_name_of(conn, username: str) -> str:
    if not username:
        return ""
    if " AI" in username or username.endswith("AI"):
        return username
    try:
        return agent_dict(conn, username).get("display_name") or username
    except Exception:
        return username


def maybe_auto_reassign_on_user_message(conn, room_id: str, insert_message_fn) -> Optional[str]:
    """If assignee empty or away/offline/busy and setting on, assign an online agent.
    insert_message_fn(room_id, body) should insert a system message.
    Returns new assignee username or None.
    """
    ensure_cs_ops_tables(conn)
    if get_setting(conn, "auto_reassign_when_away", "1") != "1":
        return None
    row = conn.execute("select assignee from cs_rooms where id=?", (room_id,)).fetchone()
    if row is None:
        return None
    cur = (row["assignee"] or "").strip()
    need = False
    if not cur:
        need = True
    else:
        st = agent_dict(conn, cur).get("status") or STATUS_OFFLINE
        if is_agent_unavailable(st):
            need = True
    if not need:
        return None
    pick = pick_online_agent(conn, exclude=cur)
    if not pick:
        return None
    new_u = pick["username"]
    if new_u == cur:
        return None
    set_room_assignee(conn, room_id, new_u, prev=cur if cur else None)
    dn = pick.get("display_name") or new_u
    try:
        insert_message_fn(room_id, "已转接给 " + dn)
    except Exception:
        pass
    return new_u


def transfer_room(conn, room_id: str, from_user: str, to_user: str, insert_message_fn) -> dict:
    """Manual transfer. Returns {ok, room fields...} or raises ValueError."""
    ensure_cs_ops_tables(conn)
    to_user = (to_user or "").strip()
    if not to_user:
        raise ValueError("to_username")
    row = conn.execute("select * from cs_rooms where id=?", (room_id,)).fetchone()
    if row is None:
        raise ValueError("room")
    staff = conn.execute(
        "select username, enabled from staff where username=?", (to_user,)
    ).fetchone()
    if staff is None or not int(staff["enabled"] or 0):
        raise ValueError("agent")
    ensure_agent_profile(conn, to_user)
    cur = (row["assignee"] or "").strip()
    from_u = (from_user or cur or "").strip()
    set_room_assignee(conn, room_id, to_user, prev=cur if cur else from_u)
    from_dn = display_name_of(conn, from_u) if from_u else "客服"
    to_dn = display_name_of(conn, to_user)
    body = "由 " + from_dn + " 转交给 " + to_dn
    try:
        insert_message_fn(room_id, body)
    except Exception:
        pass
    return {"ok": True, "assignee": to_user, "prev_assignee": cur or from_u}



def cs_tone_blocked(text: str) -> bool:
    return bool(re.search(r"哈哈|呵呵|笑着|笑呢|讥讽|开玩笑|lol|lmao|rofl", text or "", re.I))


def ai_paused_for_human(conn, room_id: str, ai_name: str = "Harbor") -> bool:
    """A person has taken this room. AI stays out until the room is handed back."""
    if room_ai_mode(conn, room_id):
        return False
    try:
        row = conn.execute("select assignee from cs_rooms where id=?", (room_id,)).fetchone()
    except Exception:
        row = None
    if row is not None:
        try:
            assignee = str((row["assignee"] if "assignee" in row.keys() else "") or "").strip()
        except Exception:
            assignee = ""
        if assignee:
            return True
    ai = (ai_name or "Harbor").strip().lower()
    try:
        rows = conn.execute(
            "select staff_user from cs_messages where room_id=? and role='staff' order by id desc limit 40",
            (room_id,),
        ).fetchall()
    except Exception:
        return False
    for item in rows:
        try:
            who = str((item["staff_user"] if "staff_user" in item.keys() else "") or "").strip()
        except Exception:
            who = ""
        if not who:
            continue
        low = who.lower()
        if low == ai or low == "harbor" or low.startswith("ai"):
            continue
        return True
    return False


def room_ai_mode(conn, room_id: str) -> bool:
    ensure_cs_ops_tables(conn)
    row = conn.execute("select ai_mode from cs_rooms where id=?", (room_id,)).fetchone()
    if row is None:
        return False
    try:
        return int(row["ai_mode"] or 0) == 1
    except Exception:
        return False


def set_room_ai_mode(conn, room_id: str, on: bool) -> None:
    ensure_cs_ops_tables(conn)
    conn.execute("update cs_rooms set ai_mode=? where id=?", (1 if on else 0, room_id))


def transfer_room_to_ai(conn, room_id: str, from_user: str, insert_message_fn) -> dict:
    """Hand room to AI auto-reply. Keeps assignee so the agent can monitor."""
    ensure_cs_ops_tables(conn)
    row = conn.execute("select * from cs_rooms where id=?", (room_id,)).fetchone()
    if row is None:
        raise ValueError("room")
    from_u = (from_user or (row["assignee"] if "assignee" in row.keys() else "") or "").strip()
    if from_u and not (row["assignee"] if "assignee" in row.keys() else ""):
        set_room_assignee(conn, room_id, from_u, prev="")
    set_room_ai_mode(conn, room_id, True)
    from_dn = display_name_of(conn, from_u) if from_u else "客服"
    ai_name = get_setting(conn, "ai_name", "Harbor") or "Harbor"
    body = "[ops]由 " + from_dn + " 转交给 AI「" + ai_name + "」（仅客服可见）"
    try:
        insert_message_fn(room_id, body)
    except Exception:
        pass
    return {"ok": True, "ai_mode": 1, "assignee": from_u or (row["assignee"] if "assignee" in row.keys() else "")}


def clear_room_ai_mode(conn, room_id: str, *, by_user: str = "", insert_message_fn=None, silent: bool = False) -> None:
    ensure_cs_ops_tables(conn)
    if not room_ai_mode(conn, room_id):
        return
    set_room_ai_mode(conn, room_id, False)
    if silent or insert_message_fn is None:
        return
    who = display_name_of(conn, by_user) if by_user else "客服"
    try:
        insert_message_fn(room_id, "[ops]" + who + " 已接回人工接待，AI 暂停")
    except Exception:
        pass


def cs_search_items(conn, q: str, limit: int = 15) -> list:
    """One catalog query. Chinese title lives in source_zh, not a second product database."""
    q = (q or "").strip()
    limit = max(1, min(int(limit or 15), 20))
    cols = "sku, names, source_zh, price_cents, image_url"
    if q:
        like = f"%{q}%"
        rows = conn.execute(
            f"""
            select {cols} from products
            where published = 1 and (
              sku like ? or ifnull(source_zh,'') like ? or ifnull(names,'') like ?
            )
            limit ?
            """,
            (like, like, like, limit),
        ).fetchall()
        if not rows:
            rows = conn.execute(
                f"""
                select {cols} from products
                where published = 1 and ifnull(offers,'') like ?
                limit ?
                """,
                (like, limit),
            ).fetchall()
    else:
        rows = conn.execute(
            f"select {cols} from products where published = 1 limit ?",
            (limit,),
        ).fetchall()
    items = []
    for row in rows:
        names = {}
        try:
            names = json.loads(row["names"] or "{}")
        except Exception:
            names = {}
        src = str(row["source_zh"] or "")
        name = ""
        if src.strip().startswith("{"):
            try:
                parsed = json.loads(src)
            except Exception:
                parsed = None
            if isinstance(parsed, dict):
                name = str(parsed.get("name") or "").strip()
        elif src.strip():
            name = src.strip()
        if not name:
            name = str(names.get("zh") or names.get("en") or row["sku"])
        cents = int(row["price_cents"] or 0)
        items.append({
            "sku": row["sku"],
            "name": name,
            "image": row["image_url"] or "",
            "price": ("$%.2f" % (cents / 100.0)) if cents else "",
            "price_cents": cents,
            "offers": [],
            "sizes": [],
        })
    return items


def _lang_key(lang: str) -> str:
    key = (lang or "en").replace("_", "-").split("-")[0].lower()
    if key in {"zh", "cn"}:
        return "zh"
    return key or "en"


def _zh_title(source_zh, names, sku: str) -> str:
    src = str(source_zh or "").strip()
    if src.startswith("{"):
        try:
            parsed = json.loads(src)
        except Exception:
            parsed = None
        if isinstance(parsed, dict) and str(parsed.get("name") or "").strip():
            return str(parsed.get("name")).strip()
    elif src:
        return src
    if isinstance(names, dict):
        return str(names.get("zh") or names.get("en") or sku)
    return sku


def _title_for(source_zh, names, lang: str, sku: str) -> str:
    if _lang_key(lang) == "zh":
        return _zh_title(source_zh, names, sku)
    if isinstance(names, dict):
        return str(names.get(_lang_key(lang)) or names.get("en") or _zh_title(source_zh, names, sku) or sku)
    return sku


def _offer_text(offer: dict, lang: str) -> str:
    src = str(offer.get("source_label") or "").strip()
    label = offer.get("label")
    if _lang_key(lang) == "zh":
        if src:
            return src
        if isinstance(label, dict):
            return str(label.get("zh") or label.get("en") or "")
        return str(label or "")
    if isinstance(label, dict):
        return str(label.get(_lang_key(lang)) or label.get("en") or src or "")
    return str(label or src or "")


def product_card_for_lang(conn, body: str, lang: str) -> str:
    """Same SKU, name and option in the viewer's language."""
    raw = str(body or "")
    if not raw.startswith("[product]"):
        return raw
    try:
        data = json.loads(raw[9:].strip() or "{}")
    except Exception:
        return raw
    if not isinstance(data, dict):
        return raw
    sku = str(data.get("sku") or "").strip()
    if not sku:
        return raw
    row = conn.execute(
        "select names, source_zh, image_url, price_cents, offers from products where sku=?",
        (sku,),
    ).fetchone()
    if row is None:
        return raw
    names = {}
    offers = []
    try:
        names = json.loads(row["names"] or "{}")
    except Exception:
        names = {}
    try:
        offers = json.loads(row["offers"] or "[]")
    except Exception:
        offers = []
    data["name"] = _title_for(row["source_zh"], names, lang, sku)
    want = str(data.get("offer_id") or data.get("option_key") or "")
    picked = None
    for offer in offers:
        if not isinstance(offer, dict) or offer.get("hold"):
            continue
        if want and str(offer.get("id") or "") == want:
            picked = offer
            break
    if picked is None and want:
        for offer in offers:
            if isinstance(offer, dict) and str(offer.get("source_label") or "") == str(data.get("option") or ""):
                picked = offer
                break
    if picked is not None:
        data["option"] = _offer_text(picked, lang)
        data["offer_id"] = str(picked.get("id") or want)
        cents = int(picked.get("price_cents") or 0)
        if cents:
            data["price"] = "$%.2f" % (cents / 100.0)
        if picked.get("image"):
            data["image"] = picked.get("image")
    if not data.get("image"):
        data["image"] = row["image_url"] or data.get("image") or ""
    if not data.get("price"):
        cents = int(row["price_cents"] or 0)
        if cents:
            data["price"] = "$%.2f" % (cents / 100.0)
    return "[product]" + json.dumps(data, ensure_ascii=False)


def product_for_visitor(conn, sku: str, lang: str) -> Optional[dict]:
    sku = (sku or "").strip()
    if not sku:
        return None
    row = conn.execute(
        "select names, source_zh, image_url, price_cents, offers from products where sku=?",
        (sku,),
    ).fetchone()
    if row is None:
        return None
    names = {}
    offers_raw = []
    try:
        names = json.loads(row["names"] or "{}")
    except Exception:
        names = {}
    try:
        offers_raw = json.loads(row["offers"] or "[]")
    except Exception:
        offers_raw = []
    offers = []
    for offer in offers_raw:
        if not isinstance(offer, dict) or offer.get("hold"):
            continue
        cents = int(offer.get("price_cents") or 0)
        offers.append({
            "id": str(offer.get("id") or ""),
            "label": _offer_text(offer, lang),
            "price": ("$%.2f" % (cents / 100.0)) if cents else "",
            "image": str(offer.get("image") or ""),
        })
    cents = int(row["price_cents"] or 0)
    return {
        "sku": sku,
        "name": _title_for(row["source_zh"], names, lang, sku),
        "image": row["image_url"] or "",
        "price": ("$%.2f" % (cents / 100.0)) if cents else "",
        "offers": offers,
    }


def cs_catalog_slim(conn, limit: int = 8000) -> list:
    """Text catalog for the desktop. No image files."""
    rows = conn.execute(
        """
        select sku, names, source_zh, price_cents, offers
        from products where published = 1
        limit ?
        """,
        (max(1, min(int(limit or 8000), 12000)),),
    ).fetchall()
    items = []
    for row in rows:
        names = {}
        offers_raw = []
        try:
            names = json.loads(row["names"] or "{}")
        except Exception:
            names = {}
        try:
            offers_raw = json.loads(row["offers"] or "[]")
        except Exception:
            offers_raw = []
        offers = []
        for offer in offers_raw:
            if not isinstance(offer, dict) or offer.get("hold"):
                continue
            offers.append({
                "id": str(offer.get("id") or ""),
                "label": _offer_text(offer, "zh"),
            })
        cents = int(row["price_cents"] or 0)
        items.append({
            "sku": row["sku"],
            "name": _zh_title(row["source_zh"], names, row["sku"]),
            "price": ("$%.2f" % (cents / 100.0)) if cents else "",
            "offers": offers,
        })
    return items


def product_detail_for_cs(conn, sku: str) -> Optional[dict]:
    """Catalog product for desk SKU picker. Returns None if missing."""
    sku = (sku or "").strip()
    if not sku:
        return None
    row = conn.execute("select * from products where sku=?", (sku,)).fetchone()
    if row is None:
        return None
    names = {}
    try:
        names = json.loads(row["names"] or "{}")
    except Exception:
        names = {}
    name = ""
    try:
        src = (row["source_zh"] if "source_zh" in row.keys() else "") or ""
    except Exception:
        src = ""
    name = ""
    if src.strip().startswith("{"):
        try:
            parsed_src = json.loads(src)
        except Exception:
            parsed_src = None
        if isinstance(parsed_src, dict):
            name = str(parsed_src.get("name") or "").strip()
    elif src.strip():
        name = src.strip()
    if not name:
        name = str(names.get("zh") or names.get("en") or sku)
    offers_raw = []
    try:
        offers_raw = json.loads(row["offers"] or "[]")
    except Exception:
        offers_raw = []
    offers = []
    sizes = []
    for offer in offers_raw:
        if not isinstance(offer, dict):
            continue
        if offer.get("hold"):
            continue
        src_label = str(offer.get("source_label") or "").strip()
        label = offer.get("label")
        zh_label = ""
        if isinstance(label, dict):
            zh_label = str(label.get("zh") or "").strip()
            en_label = str(label.get("en") or "").strip()
        else:
            en_label = str(label or "").strip()
        text = src_label or zh_label or en_label
        oid = str(offer.get("id") or text or "")
        if not text:
            text = oid or "选项"
        cents = int(offer.get("price_cents") or 0)
        price = ("$%.2f" % (cents / 100.0)) if cents else ""
        img = str(offer.get("image") or "")
        offers.append({"id": oid, "label": text, "price": price, "image": img, "price_cents": cents})
        sizes.append(text)
    specs = {}
    try:
        specs = json.loads(row["specs"] or "{}")
    except Exception:
        specs = {}
    size_spec = str((specs or {}).get("size") or "").strip()
    if size_spec and not sizes:
        for part in [p.strip() for p in size_spec.replace("，", ",").split(",") if p.strip()]:
            sizes.append(part)
            offers.append({"id": part, "label": part, "price": "", "image": "", "price_cents": 0})
    try:
        image = (row["image_url"] if "image_url" in row.keys() and row["image_url"] else "") or (
            "/static/products/%s.svg" % sku
        )
    except Exception:
        image = "/static/products/%s.svg" % sku
    cents = int(row["price_cents"] or 0)
    if offers:
        live = [o for o in offers if o.get("price_cents")]
        if live:
            cents = min(o["price_cents"] for o in live) or cents
    price = ("$%.2f" % (cents / 100.0)) if cents else ""
    return {
        "sku": sku,
        "name": name,
        "image": image,
        "price": price,
        "price_cents": cents,
        "sizes": sizes,
        "offers": offers,
    }

