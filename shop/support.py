# -*- coding: utf-8 -*-
"""Harbor realtime CS chat: rooms, messages, long-poll + websocket."""
from __future__ import annotations

import threading
import time

import asyncio
import json
import secrets
from shop.cs_ops import (
    STATUS_BUSY, STATUS_LABELS_ZH, STATUS_OFFLINE, STATUS_ONLINE,
    agent_dict, all_settings, any_agent_online, claim_room_if_unassigned,
    client_ip_from_request, detect_lang, display_name_of, ensure_cs_ops_tables,
    filter_rooms_for_agent, generate_cs_ai_reply, get_setting, list_canned,
    list_cs_agents, list_stickers, lookup_geo, maybe_auto_reassign_on_user_message,
    order_context_for_room, cart_context_for_room, order_detail, orders_for_email, _order_line_titles, prepare_staff_message, prepare_user_message,
    product_detail_for_cs, product_card_for_lang, product_for_visitor, cs_catalog_slim, cs_search_items, ai_paused_for_human, room_ai_mode, room_visible_to_agent, set_agent_status, set_setting,
    clear_room_ai_mode, staff_is_admin, transfer_room, transfer_room_to_ai, update_agent_profile, wants_human_handoff,
    typing_delay_seconds,
    split_cs_ai_bubbles
)
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import base64
import uuid
from pathlib import Path

from fastapi import Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

CS_UPLOAD_DIR = Path(__file__).resolve().parent / "static" / "cs"
ALLOWED_IMG_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_IMG_BYTES = 5 * 1024 * 1024


def ensure_cs_upload_dir() -> None:
    CS_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _is_img_body(body: str) -> bool:
    return str(body or "").startswith("[img]")


def _is_product_body(body: str) -> bool:
    return str(body or "").startswith("[product]")


def _is_order_body(body: str) -> bool:
    return str(body or "").startswith("[order]")


def _is_cart_body(body: str) -> bool:
    return str(body or "").strip().startswith("[cart]")


def _is_special_body(body: str) -> bool:
    return _is_img_body(body) or _is_product_body(body) or _is_order_body(body) or _is_cart_body(body)


def _normalize_img_body(body: str = "", image_url: str = "") -> str:
    url = _clip(image_url, 500)
    if url.startswith("/static/cs/"):
        return "[img]" + url
    raw = str(body or "").strip()
    if raw.startswith("[img]"):
        part = raw[5:].strip().split()[0] if raw[5:].strip() else ""
        if part.startswith("/static/cs/"):
            return "[img]" + part
    return ""


def save_cs_image_bytes(data: bytes, filename: str = "") -> str:
    ensure_cs_upload_dir()
    raw = data or b""
    if len(raw) > MAX_IMG_BYTES:
        raise ValueError("too_large")
    if len(raw) < 24:
        raise ValueError("empty")
    ext = Path(filename or "").suffix.lower()
    if ext == ".jpeg":
        ext = ".jpg"
    if ext not in ALLOWED_IMG_EXT:
        if raw[:3] == b"\xff\xd8\xff":
            ext = ".jpg"
        elif raw[:8] == b"\x89PNG\r\n\x1a\n":
            ext = ".png"
        elif raw[:6] in (b"GIF87a", b"GIF89a"):
            ext = ".gif"
        elif len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
            ext = ".webp"
        else:
            raise ValueError("type")
    name = f"{uuid.uuid4().hex}{ext}"
    path = CS_UPLOAD_DIR / name
    path.write_bytes(raw)
    return f"/static/cs/{name}"


async def _read_upload_payload(request: Request):
    ctype = (request.headers.get("content-type") or "").lower()
    if "application/json" in ctype:
        payload = await request.json()
        raw = payload.get("data_base64") or payload.get("dataUrl") or payload.get("data_url") or ""
        raw = str(raw)
        if raw.startswith("data:") and "," in raw:
            raw = raw.split(",", 1)[1]
        data = base64.b64decode(raw)
        filename = str(payload.get("filename") or "image.png")
        return data, filename, payload
    form = await request.form()
    payload = dict(form)
    if form.get("data_base64") or form.get("dataUrl") or form.get("data_url"):
        raw = str(form.get("data_base64") or form.get("dataUrl") or form.get("data_url") or "")
        if raw.startswith("data:") and "," in raw:
            raw = raw.split(",", 1)[1]
        data = base64.b64decode(raw)
        filename = str(form.get("filename") or "image.png")
        return data, filename, payload
    upload = form.get("file")
    if upload is None:
        raise ValueError("file")
    data = await upload.read()
    filename = getattr(upload, "filename", None) or "image.jpg"
    return data, str(filename), payload


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_cs_tables(conn) -> None:
    conn.execute(
        """
        create table if not exists cs_rooms (
            id text primary key,
            visitor_id text not null,
            email text not null default '',
            status text not null default 'open',
            current_sku text not null default '',
            current_name text not null default '',
            current_image text not null default '',
            current_price text not null default '',
            history_json text not null default '[]',
            created_at text not null,
            updated_at text not null,
            last_user_at text not null default '',
            last_staff_at text not null default '',
            unread_staff integer not null default 0,
            unread_user integer not null default 0
        )
        """
    )
    conn.execute(
        """
        create table if not exists cs_messages (
            id integer primary key,
            room_id text not null,
            role text not null,
            body text not null,
            created_at text not null,
            staff_user text not null default ''
        )
        """
    )
    conn.execute("create index if not exists cs_messages_room on cs_messages (room_id, id)")
    conn.execute("create index if not exists cs_rooms_updated on cs_rooms (updated_at desc)")
    conn.execute("create index if not exists cs_rooms_visitor on cs_rooms (visitor_id, updated_at desc)")
    try:
        ensure_cs_ops_tables(conn)
    except Exception:
        pass


class SupportBus:
    """Wake long-poll / WS waiters when a room or inbox changes."""

    def __init__(self) -> None:
        self._room_waiters: dict[str, list[asyncio.Future]] = defaultdict(list)
        self._inbox_waiters: list[asyncio.Future] = []
        self._ws: dict[str, set[WebSocket]] = defaultdict(set)

    def _wake(self, waiters: list[asyncio.Future]) -> None:
        for fut in list(waiters):
            if not fut.done():
                fut.set_result(True)

    def notify_room(self, room_id: str) -> None:
        self._wake(self._room_waiters.pop(room_id, []))
        # schedule WS broadcast from sync context
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcast_ws(room_id))
        except RuntimeError:
            pass

    def notify_inbox(self) -> None:
        waiters, self._inbox_waiters = self._inbox_waiters, []
        self._wake(waiters)

    async def wait_room(self, room_id: str, timeout: float) -> bool:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._room_waiters[room_id].append(fut)
        try:
            await asyncio.wait_for(asyncio.shield(fut), timeout)
            return True
        except asyncio.TimeoutError:
            return False
        finally:
            lst = self._room_waiters.get(room_id) or []
            if fut in lst:
                lst.remove(fut)

    async def wait_inbox(self, timeout: float) -> bool:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._inbox_waiters.append(fut)
        try:
            await asyncio.wait_for(asyncio.shield(fut), timeout)
            return True
        except asyncio.TimeoutError:
            return False
        finally:
            if fut in self._inbox_waiters:
                self._inbox_waiters.remove(fut)

    def add_ws(self, room_id: str, ws: WebSocket) -> None:
        self._ws[room_id].add(ws)

    def drop_ws(self, room_id: str, ws: WebSocket) -> None:
        self._ws[room_id].discard(ws)

    async def _broadcast_ws(self, room_id: str) -> None:
        dead = []
        for ws in list(self._ws.get(room_id) or []):
            try:
                await ws.send_json({"type": "ping", "room_id": room_id})
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._ws[room_id].discard(ws)


BUS = SupportBus()



# In-memory typing indicators: room_id -> {side, name, until}
_TYPING: dict[str, dict] = {}
_TYPING_LOCK = threading.Lock()


def set_room_typing(room_id: str, *, side: str, name: str, ttl: float = 6.0, notify: bool = True) -> None:
    rid = str(room_id or "").strip()
    if not rid:
        return
    with _TYPING_LOCK:
        _TYPING[rid] = {
            "side": str(side or "staff"),
            "name": str(name or "")[:64],
            "until": time.time() + max(1.0, float(ttl or 6.0)),
        }
    if notify:
        try:
            BUS.notify_room(rid)
        except Exception:
            pass


def clear_room_typing(room_id: str, *, side: str | None = None, notify: bool = True) -> None:
    rid = str(room_id or "").strip()
    if not rid:
        return
    changed = False
    with _TYPING_LOCK:
        cur = _TYPING.get(rid)
        if not cur:
            return
        if side is None or str(cur.get("side") or "") == str(side):
            _TYPING.pop(rid, None)
            changed = True
    if changed and notify:
        try:
            BUS.notify_room(rid)
        except Exception:
            pass


def get_room_typing(room_id: str) -> dict | None:
    rid = str(room_id or "").strip()
    if not rid:
        return None
    with _TYPING_LOCK:
        cur = _TYPING.get(rid)
        if not cur:
            return None
        if time.time() > float(cur.get("until") or 0):
            _TYPING.pop(rid, None)
            return None
        return {
            "active": True,
            "side": cur.get("side") or "staff",
            "name": cur.get("name") or "",
        }




def typing_for_buyer(typing: dict | None, *, display_name: str = "Harbor") -> dict | None:
    """Buyer poll/messages must not expose side=ai or AI branding."""
    if not typing:
        return typing
    out = dict(typing)
    side = str(out.get("side") or "")
    if side == "ai":
        out["side"] = "staff"
    name = str(out.get("name") or "")
    if (not name) or ("AI" in name) or side == "ai":
        out["name"] = str(display_name or "Harbor")[:64]
    out["active"] = True
    return out


def _clip(s: Any, n: int) -> str:
    return str(s or "").strip()[:n]



def _parse_cart_json(raw: Any) -> list:
    try:
        from shop.cs_ops import normalize_cart_lines
        return normalize_cart_lines(raw)
    except Exception:
        if isinstance(raw, str):
            try:
                data = json.loads(raw or "[]")
            except Exception:
                return []
            return data if isinstance(data, list) else []
        return raw if isinstance(raw, list) else []


def _parse_history(raw: Any) -> list[dict]:
    items = raw
    if isinstance(raw, str):
        try:
            items = json.loads(raw or "[]")
        except Exception:
            items = []
    if not isinstance(items, list):
        return []
    out = []
    for it in items[:30]:
        if not isinstance(it, dict):
            continue
        sku = _clip(it.get("sku"), 80)
        if not sku:
            continue
        out.append(
            {
                "sku": sku,
                "name": _clip(it.get("name"), 200),
                "image": _clip(it.get("image"), 500),
                "price": _clip(it.get("price"), 40),
                "ts": int(it.get("ts") or 0),
            }
        )
    return out


def room_dict(row) -> dict:
    hist = []
    try:
        hist = json.loads(row["history_json"] or "[]")
    except Exception:
        hist = []
    tags = []
    try:
        tags = json.loads(row["tags_json"] if "tags_json" in row.keys() else "[]")
    except Exception:
        tags = []
    def _g(k, default=""):
        try:
            return row[k] if k in row.keys() else default
        except Exception:
            return default
    geo_label = " / ".join([p for p in (_g("geo_country"), _g("geo_region"), _g("geo_city")) if p])
    if not geo_label and _g("client_ip"):
        geo_label = "本地/内网" if str(_g("client_ip")).startswith(("127.", "10.", "192.168.")) else ""
    return {
        "id": row["id"],
        "visitor_id": row["visitor_id"],
        "email": row["email"],
        "status": row["status"],
        "current": {
            "sku": row["current_sku"],
            "name": row["current_name"],
            "image": row["current_image"],
            "price": row["current_price"],
        },
        "history": hist if isinstance(hist, list) else [],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "last_user_at": row["last_user_at"],
        "last_staff_at": row["last_staff_at"],
        "unread_staff": int(row["unread_staff"] or 0),
        "unread_user": int(row["unread_user"] or 0),
        "client_ip": _g("client_ip"),
        "geo": {
            "country": _g("geo_country"),
            "region": _g("geo_region"),
            "city": _g("geo_city"),
            "label": geo_label,
        },
        "user_lang": _g("user_lang"),
        "assignee": _g("assignee"),
        "prev_assignee": _g("prev_assignee"),
        "ai_mode": int(_g("ai_mode") or 0),
        "tags": tags if isinstance(tags, list) else [],
        "cart": _parse_cart_json(_g("cart_json", "[]")),
        "cart_json": _g("cart_json", "[]"),
    }


def msg_dict(row) -> dict:
    def _g(k, default=""):
        try:
            return row[k] if k in row.keys() else default
        except Exception:
            return default
    return {
        "id": int(row["id"]),
        "room_id": row["room_id"],
        "role": row["role"],
        "body": row["body"],
        "body_original": _g("body_original") or row["body"],
        "body_zh": _g("body_zh") or (row["body"] if row["role"] == "staff" else ""),
        "lang": _g("lang"),
        "translated": int(_g("translated") or 0),
        "created_at": row["created_at"],
        "staff_user": row["staff_user"] or "",
    }


def list_messages(conn, room_id: str, after_id: int = 0, limit: int = 200) -> list[dict]:
    rows = conn.execute(
        "select * from cs_messages where room_id = ? and id > ? order by id asc limit ?",
        (room_id, int(after_id or 0), int(limit)),
    ).fetchall()
    return [msg_dict(r) for r in rows]


def get_room(conn, room_id: str):
    return conn.execute("select * from cs_rooms where id = ?", (room_id,)).fetchone()



def save_room_cart(conn, room_id: str, lines: list) -> None:
    ensure_cs_tables(conn)
    try:
        cols = {r["name"] for r in conn.execute("pragma table_info(cs_rooms)").fetchall()}
    except Exception:
        cols = set()
    if "cart_json" not in cols:
        try:
            conn.execute("alter table cs_rooms add column cart_json text not null default '[]'")
        except Exception:
            return
    payload = json.dumps(lines or [], ensure_ascii=False)
    conn.execute("update cs_rooms set cart_json=? where id=?", (payload, room_id))


def extract_cart_from_request(request: Request, payload: dict | None = None) -> list:
    payload = payload if isinstance(payload, dict) else {}
    from shop.cs_ops import normalize_cart_lines
    payload_lines = normalize_cart_lines(payload.get("cart") or payload.get("cart_lines") or payload.get("cart_items"))
    cookie_raw = ""
    try:
        cookie_raw = request.cookies.get("cart") or ""
    except Exception:
        cookie_raw = ""
    cookie_lines = normalize_cart_lines(cookie_raw)
    # The shop cookie is the cart the customer will check out. Keep it when present.
    if cookie_lines:
        names = {str(line.get("sku") or ""): str(line.get("name") or "") for line in payload_lines}
        for line in cookie_lines:
            if not line.get("name"):
                line["name"] = names.get(str(line.get("sku") or ""), "")
        return cookie_lines
    return payload_lines


def push_open_room_cart(conn, request, lines) -> None:
    """Customer changed the shop cart. Snapshot it onto the open chat and wake the desk."""
    try:
        vid = ""
        try:
            vid = (request.cookies.get("harbor_vid") or "").strip()
        except Exception:
            vid = ""
        if not vid:
            return
        row = conn.execute(
            "select id from cs_rooms where visitor_id = ? and status = 'open' order by updated_at desc limit 1",
            (vid,),
        ).fetchone()
        if row is None:
            return
        room_id = row["id"]
        payload = []
        for line in lines or []:
            sku = str(line.get("sku") or "").strip()
            if not sku:
                continue
            try:
                qty = int(line.get("qty") or 0)
            except Exception:
                qty = 0
            if qty <= 0:
                continue
            payload.append({"sku": sku, "qty": qty, "name": str(line.get("name") or "")[:120]})
        save_room_cart(conn, room_id, payload)
        conn.execute("update cs_rooms set updated_at = ? where id = ?", (utc_now(), room_id))
        BUS.notify_room(room_id)
    except Exception:
        return


def update_context(conn, room_id: str, ctx: dict) -> None:
    hist = _parse_history(ctx.get("history"))
    conn.execute(
        """
        update cs_rooms set
          current_sku = ?, current_name = ?, current_image = ?, current_price = ?,
          history_json = ?, updated_at = ?
        where id = ?
        """,
        (
            _clip(ctx.get("sku"), 80),
            _clip(ctx.get("name"), 200),
            _clip(ctx.get("image"), 500),
            _clip(ctx.get("price"), 40),
            json.dumps(hist, ensure_ascii=False),
            utc_now(),
            room_id,
        ),
    )


def open_or_resume_room(conn, *, visitor_id: str, email: str, ctx: dict) -> str:
    ensure_cs_tables(conn)
    vid = _clip(visitor_id, 64) or secrets.token_hex(8)
    email = _clip(email, 120).lower()
    row = conn.execute(
        """
        select id from cs_rooms
        where visitor_id = ? and status = 'open'
        order by updated_at desc limit 1
        """,
        (vid,),
    ).fetchone()
    now = utc_now()
    if row:
        room_id = row["id"]
        update_context(conn, room_id, ctx)
        if email:
            conn.execute("update cs_rooms set email = ? where id = ? and email = ''", (email, room_id))
        return room_id

    room_id = secrets.token_hex(12)
    hist = _parse_history(ctx.get("history"))
    conn.execute(
        """
        insert into cs_rooms (
          id, visitor_id, email, status,
          current_sku, current_name, current_image, current_price,
          history_json, created_at, updated_at
        ) values (?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            room_id,
            vid,
            email,
            _clip(ctx.get("sku"), 80),
            _clip(ctx.get("name"), 200),
            _clip(ctx.get("image"), 500),
            _clip(ctx.get("price"), 40),
            json.dumps(hist, ensure_ascii=False),
            now,
            now,
        ),
    )
    # system greeting
    conn.execute(
        "insert into cs_messages (room_id, role, body, created_at) values (?, 'system', ?, ?)",
        (room_id, "Harbor support is online. Ask about this product, shipping, or your order.", now),
    )
    BUS.notify_inbox()
    return room_id


def insert_message(
    conn,
    *,
    room_id: str,
    role: str,
    body: str,
    staff_user: str = "",
    body_original: str = "",
    body_zh: str = "",
    lang: str = "",
    translated: int = 0,
) -> dict:
    ensure_cs_tables(conn)
    body = _clip(body, 2000)
    if not body:
        raise ValueError("empty")
    now = utc_now()
    cur = conn.execute(
        """
        insert into cs_messages (
          room_id, role, body, created_at, staff_user,
          body_original, body_zh, lang, translated
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            room_id,
            role,
            body,
            now,
            staff_user,
            _clip(body_original or body, 2000),
            _clip(body_zh or "", 2000),
            _clip(lang, 16),
            int(translated or 0),
        ),
    )
    mid = cur.lastrowid
    if role == "user":
        conn.execute(
            """
            update cs_rooms set updated_at = ?, last_user_at = ?,
              unread_staff = unread_staff + 1, unread_user = 0, status = 'open'
            where id = ?
            """,
            (now, now, room_id),
        )
    elif role == "staff":
        conn.execute(
            """
            update cs_rooms set updated_at = ?, last_staff_at = ?,
              unread_user = unread_user + 1, unread_staff = 0
            where id = ?
            """,
            (now, now, room_id),
        )
    else:
        conn.execute("update cs_rooms set updated_at = ? where id = ?", (now, room_id))
    BUS.notify_room(room_id)
    BUS.notify_inbox()
    row = conn.execute("select * from cs_messages where id = ?", (mid,)).fetchone()
    return msg_dict(row)



def touch_room_network(conn, request, room_id: str, *, lang_hint: str = "") -> None:
    """Record client IP/geo (and optional lang) once per room when still empty."""
    try:
        ensure_cs_ops_tables(conn)
        room = get_room(conn, room_id)
        if room is None:
            return
        existing_ip = ""
        try:
            existing_ip = room["client_ip"] if "client_ip" in room.keys() else ""
        except Exception:
            existing_ip = ""
        ip = client_ip_from_request(request)
        if ip and not existing_ip:
            show_geo = get_setting(conn, "show_ip_geo", "1") == "1"
            geo = lookup_geo(ip) if show_geo else {"country": "", "region": "", "city": "", "label": ""}
            # private / local: still store IP and a readable place label
            country = geo.get("country") or ""
            region = geo.get("region") or ""
            city = geo.get("city") or ""
            if not (country or region or city):
                label = geo.get("label") or ""
                if not label and (
                    ip.startswith(("127.", "10.", "192.168."))
                    or ip in {"::1", "localhost"}
                    or ip.startswith("172.")
                ):
                    label = "本地/内网"
                if label:
                    city = label
            conn.execute(
                """
                update cs_rooms set client_ip=?, geo_country=?, geo_region=?, geo_city=?
                where id=?
                """,
                (ip, country, region, city, room_id),
            )
        hint = _clip(lang_hint, 16)
        if hint:
            conn.execute(
                "update cs_rooms set user_lang=? where id=? and (user_lang='' or user_lang is null)",
                (hint[:8], room_id),
            )
    except Exception:
        pass


def mount_support(app, *, conn, render, require_staff, buyer_email, get_translator=None, get_complete=None):
    ensure_cs_tables(conn)
    ensure_cs_upload_dir()

    def _room_lang(room_id: str) -> str:
        room = get_room(conn, room_id)
        if room is None:
            return "en"
        try:
            return (room["user_lang"] if "user_lang" in room.keys() else "") or "en"
        except Exception:
            return "en"

    def messages_for_user(room_id: str, after_id: int = 0, limit: int = 200):
        msgs = list_messages(conn, room_id, after_id=after_id, limit=limit)
        ai_display = get_setting(conn, "ai_name", "Harbor") or "Harbor"
        lang = _room_lang(room_id)
        out = []
        for m in msgs:
            body = str(m.get("body") or "")
            # ops / internal transfer notes: desk only
            if m.get("role") == "system" and (body.startswith("[ops]") or "转交给 AI" in body or "已接回人工" in body):
                continue
            item = dict(m)
            if body.startswith("[product]"):
                item["body"] = product_card_for_lang(conn, body, lang)
            elif m.get("role") == "staff":
                item["body"] = m.get("body_original") or m.get("body")
            elif m.get("role") == "user":
                item["body"] = m.get("body_original") or m.get("body")
            if m.get("role") == "staff":
                su = str(item.get("staff_user") or "")
                # Never show AI branding on the buyer side
                if "AI" in su:
                    item["staff_user"] = ai_display
            out.append(item)
        return out

    def messages_for_staff(room_id: str, after_id: int = 0, limit: int = 200):
        msgs = list_messages(conn, room_id, after_id=after_id, limit=limit)
        out = []
        for m in msgs:
            item = dict(m)
            body = str(m.get("body") or "")
            if body.startswith("[product]"):
                item["body"] = product_card_for_lang(conn, body, "zh")
                item["body_user_original"] = product_card_for_lang(conn, m.get("body_original") or body, _room_lang(room_id))
            elif m.get("role") == "user":
                item["body"] = m.get("body_zh") or m.get("body")
                item["body_user_original"] = m.get("body_original") or m.get("body")
            out.append(item)
        return out

    def rooms_for_staff(staff_username: str, status: str = "open", q: str = "", limit: int = 200):
        ensure_cs_ops_tables(conn)
        status = status if status in {"open", "closed"} else "open"
        q = (q or "").strip()
        sql = "select * from cs_rooms where status = ?"
        args = [status]
        if q:
            sql += " and (email like ? or visitor_id like ? or current_sku like ? or current_name like ?)"
            like = f"%{q}%"
            args.extend([like, like, like, like])
        sql += " order by updated_at desc limit ?"
        args.append(int(limit))
        rooms = [room_dict(r) for r in conn.execute(sql, args).fetchall()]
        return filter_rooms_for_agent(conn, rooms, staff_username)

    def open_unread_for_staff(staff_username: str):
        ensure_cs_ops_tables(conn)
        rooms = [room_dict(r) for r in conn.execute(
            "select * from cs_rooms where status='open' order by updated_at desc limit 500"
        ).fetchall()]
        visible = filter_rooms_for_agent(conn, rooms, staff_username)
        unread_n = sum(int(r.get("unread_staff") or 0) for r in visible)
        open_n = len(visible)
        return open_n, unread_n

    def maybe_ai_reply(room_id: str, user_text: str) -> None:
        ai_name = "Harbor"
        typing_on = False
        try:
            ensure_cs_ops_tables(conn)
            if get_setting(conn, "ai_enabled", "1") != "1":
                return
            if _is_special_body(user_text):
                return
            if wants_human_handoff(user_text, get_setting(conn, "ai_handoff_keywords", "")):
                clear_room_ai_mode(conn, room_id, silent=True)
                insert_message(
                    conn,
                    room_id=room_id,
                    role="system",
                    body="正在为您转接人工客服，请稍候～",
                )
                return
            room_row = get_room(conn, room_id)
            if room_row is None:
                return
            room = room_dict(room_row)
            forced_ai = int(room.get("ai_mode") or 0) == 1
            only_off = get_setting(conn, "ai_only_when_offline", "0") == "1"
            if only_off and any_agent_online(conn) and not forced_ai:
                return
            # Latest buyer message language wins — do not stick to stale room.user_lang.
            msg_lang = detect_lang(user_text, fallback=(room.get("user_lang") or "en"))
            room["user_lang"] = msg_lang
            try:
                conn.execute("update cs_rooms set user_lang=? where id=?", (msg_lang, room_id))
            except Exception:
                pass
            ai_name = get_setting(conn, "ai_name", "Harbor") or "Harbor"
            if ai_paused_for_human(conn, room_id, ai_name):
                return
            set_room_typing(room_id, side="ai", name=ai_name, ttl=12.0, notify=True)
            typing_on = True
            complete = None
            try:
                complete = get_complete() if get_complete else None
            except Exception:
                complete = None
            persona = get_setting(conn, "ai_persona", "")
            recent = messages_for_staff(room_id)
            order_ctx = order_context_for_room(conn, room)
            cart_ctx = cart_context_for_room(conn, room)
            if not (room.get("history") or []):
                try:
                    vid = str(room.get("visitor_id") or "")
                    if vid:
                        vrows = conn.execute(
                            "select sku from visits where visitor=? and kind='product' and ifnull(sku,'')!='' order by id desc limit 8",
                            (vid,),
                        ).fetchall()
                        hist = []
                        for vr in vrows:
                            sku = str(vr["sku"] if hasattr(vr, "keys") else vr[0] or "")
                            if not sku:
                                continue
                            from shop.cs_ops import _product_display_name
                            hist.append({"sku": sku, "name": _product_display_name(conn, sku), "price": "", "image": ""})
                        if hist:
                            room["history"] = hist
                except Exception:
                    pass
            text = generate_cs_ai_reply(
                complete,
                room,
                recent,
                persona=persona,
                ai_name=ai_name,
                user_text=user_text,
                order_ctx=order_ctx,
                cart_ctx=cart_ctx,
            )
            if not text:
                return
            bubbles = split_cs_ai_bubbles(text) or [text]
            translate_on = get_setting(conn, "translate_enabled", "1") == "1"
            translate = None
            try:
                translate = get_translator() if get_translator else None
            except Exception:
                translate = None
            for bi, bubble in enumerate(bubbles):
                if ai_paused_for_human(conn, room_id, ai_name):
                    break
                delay = typing_delay_seconds(bubble)
                deadline = time.time() + delay
                while True:
                    left = deadline - time.time()
                    if left <= 0:
                        break
                    set_room_typing(room_id, side="ai", name=ai_name, ttl=8.0, notify=False)
                    time.sleep(min(2.5, left))
                if ai_paused_for_human(conn, room_id, ai_name):
                    break
                body_zh = bubble
                if translate_on and translate and (msg_lang or "en")[:2] != "zh":
                    try:
                        body_zh = translate(bubble, msg_lang or "en", "zh") or bubble
                    except Exception:
                        body_zh = bubble
                insert_message(
                    conn,
                    room_id=room_id,
                    role="staff",
                    body=body_zh,
                    staff_user=ai_name,
                    body_original=bubble,
                    body_zh=body_zh,
                    lang=msg_lang or "",
                    translated=1 if body_zh != bubble else 0,
                )
                if bi < len(bubbles) - 1:
                    set_room_typing(room_id, side="ai", name=ai_name, ttl=6.0, notify=True)
                    time.sleep(0.6)
        except Exception:
            pass
        finally:
            if typing_on:
                clear_room_typing(room_id, side="ai", notify=True)

    def visitor_id(request: Request, payload=None) -> str:
        payload = payload or {}
        header_vid = request.headers.get("x-harbor-vid") or ""
        return (
            _clip(payload.get("visitor_id"), 64)
            or _clip(header_vid, 64)
            or getattr(request.state, "visitor", None)
            or request.cookies.get("harbor_vid")
            or secrets.token_hex(8)
        )

    def can_access_room(request: Request, room, payload=None) -> bool:
        if room is None:
            return False
        # staff always
        try:
            require_staff(request)
            return True
        except Exception:
            pass
        vid = visitor_id(request, payload)
        return bool(vid) and room["visitor_id"] == vid

    @app.post("/api/cs/open")
    async def cs_open(request: Request):
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        ctx = payload.get("current") if isinstance(payload.get("current"), dict) else {}
        if not ctx:
            ctx = {
                "sku": payload.get("sku"),
                "name": payload.get("name"),
                "image": payload.get("image"),
                "price": payload.get("price"),
            }
        ctx["history"] = payload.get("history") or []
        email = _clip(payload.get("email") or buyer_email(request) or "", 120).lower()
        vid = visitor_id(request, payload)
        room_id = open_or_resume_room(conn, visitor_id=vid, email=email, ctx=ctx)
        cart_lines = extract_cart_from_request(request, payload)
        if cart_lines:
            save_room_cart(conn, room_id, cart_lines)
        touch_room_network(
            conn, request, room_id,
            lang_hint=_clip(payload.get("lang") or payload.get("locale") or "", 16),
        )
        room = get_room(conn, room_id)
        msgs = messages_for_user(room_id, after_id=0)
        resp = JSONResponse({"ok": True, "room": room_dict(room), "messages": msgs})
        if not request.cookies.get("harbor_vid"):
            resp.set_cookie("harbor_vid", vid, max_age=31536000, httponly=True, samesite="lax", path="/")
        return resp

    @app.post("/api/cs/send")
    async def cs_send(request: Request):
        try:
            payload = await request.json()
        except Exception:
            form = await request.form()
            payload = dict(form)
        room_id = _clip(payload.get("room_id"), 64)
        body = _clip(payload.get("body"), 2000)
        img_body = _normalize_img_body(body, payload.get("image_url") or "")
        if img_body:
            body = img_body
        room = get_room(conn, room_id)
        if room is None or not can_access_room(request, room, payload):
            return JSONResponse({"ok": False, "error": "room"}, status_code=404)
        if room["status"] == "closed":
            conn.execute("update cs_rooms set status = 'open' where id = ?", (room_id,))
        cart_lines = extract_cart_from_request(request, payload)
        if cart_lines:
            save_room_cart(conn, room_id, cart_lines)
        touch_room_network(
            conn, request, room_id,
            lang_hint=_clip(payload.get("lang") or payload.get("locale") or "", 16),
        )
        # optional context refresh on send
        if isinstance(payload.get("current"), dict) or payload.get("sku"):
            ctx = payload.get("current") if isinstance(payload.get("current"), dict) else payload
            ctx = dict(ctx)
            ctx["history"] = payload.get("history") or json.loads(room["history_json"] or "[]")
            update_context(conn, room_id, ctx)
        ensure_cs_ops_tables(conn)

        def _after_user_msg(msg_obj):
            def _sys(rid, body_sys):
                insert_message(conn, room_id=rid, role="system", body=body_sys)
            maybe_auto_reassign_on_user_message(conn, room_id, _sys)
            room2 = get_room(conn, room_id)
            return JSONResponse({
                "ok": True,
                "message": msg_obj,
                "messages": messages_for_user(room_id),
                "room": room_dict(room2) if room2 else None,
            })

        if _is_special_body(body):
            try:
                msg = insert_message(
                    conn,
                    room_id=room_id,
                    role="user",
                    body=body,
                    body_original=body,
                    body_zh=body,
                    lang="",
                    translated=0,
                )
            except ValueError:
                return JSONResponse({"ok": False, "error": "empty"}, status_code=400)
            if not (_is_product_body(body) or _is_order_body(body)):
                threading.Thread(target=maybe_ai_reply, args=(room_id, body), daemon=True).start()
            return _after_user_msg(msg)
        translate_on = get_setting(conn, "translate_enabled", "1") == "1"
        translate = None
        try:
            translate = get_translator() if get_translator else None
        except Exception:
            translate = None
        room_lang = ""
        try:
            room_lang = room["user_lang"] if "user_lang" in room.keys() else ""
        except Exception:
            room_lang = ""
        prepared = prepare_user_message(translate, body, room_lang or "", translate_on)
        # Always refresh room lang from this message (buyer may switch language).
        if prepared.get("lang"):
            conn.execute(
                "update cs_rooms set user_lang=? where id=?",
                (prepared["lang"], room_id),
            )
        try:
            msg = insert_message(
                conn,
                room_id=room_id,
                role="user",
                body=prepared["body_store"],
                body_original=prepared.get("body_original") or body,
                body_zh=prepared.get("body_zh") or "",
                lang=prepared.get("lang") or "",
                translated=int(prepared.get("translated") or 0),
            )
        except ValueError:
            return JSONResponse({"ok": False, "error": "empty"}, status_code=400)
        threading.Thread(target=maybe_ai_reply, args=(room_id, body), daemon=True).start()
        def _sys2(rid, body_sys):
            insert_message(conn, room_id=rid, role="system", body=body_sys)
        maybe_auto_reassign_on_user_message(conn, room_id, _sys2)
        room = get_room(conn, room_id)
        return JSONResponse({"ok": True, "message": msg, "messages": messages_for_user(room_id), "room": room_dict(room) if room else None})

    @app.get("/api/cs/messages")
    async def cs_messages(request: Request):
        room_id = _clip(request.query_params.get("room_id"), 64)
        after_id = int(request.query_params.get("after") or 0)
        payload = {"visitor_id": request.query_params.get("visitor_id")}
        room = get_room(conn, room_id)
        if room is None or not can_access_room(request, room, payload):
            return JSONResponse({"ok": False, "error": "room"}, status_code=404)
        touch_room_network(conn, request, room_id)
        # mark user unread cleared when client fetches
        if room["visitor_id"] == visitor_id(request, payload):
            conn.execute("update cs_rooms set unread_user = 0 where id = ?", (room_id,))
        return JSONResponse({"ok": True, "messages": messages_for_user(room_id, after_id=after_id), "room": room_dict(room)})


    @app.get("/api/cs/poll")
    async def cs_poll(request: Request):
        room_id = _clip(request.query_params.get("room_id"), 64)
        after_id = int(request.query_params.get("after") or 0)
        timeout = float(request.query_params.get("timeout") or 20)
        timeout = max(1.0, min(timeout, 25.0))
        payload = {"visitor_id": request.query_params.get("visitor_id")}
        room = get_room(conn, room_id)
        if room is None or not can_access_room(request, room, payload):
            return JSONResponse({"ok": False, "error": "room"}, status_code=404)
        touch_room_network(conn, request, room_id)
        msgs = messages_for_user(room_id, after_id=after_id)
        ai_display = get_setting(conn, "ai_name", "Harbor") or "Harbor"
        typing = typing_for_buyer(get_room_typing(room_id), display_name=ai_display)
        if msgs:
            return JSONResponse({
                "ok": True,
                "messages": msgs,
                "room": room_dict(get_room(conn, room_id)),
                "typing": typing,
            })
        await BUS.wait_room(room_id, timeout)
        room = get_room(conn, room_id)
        return JSONResponse({
            "ok": True,
            "messages": messages_for_user(room_id, after_id=after_id),
            "room": room_dict(room) if room else None,
            "typing": typing_for_buyer(get_room_typing(room_id), display_name=ai_display),
        })

    @app.websocket("/api/cs/ws")
    async def cs_ws(ws: WebSocket):
        await ws.accept()
        room_id = _clip(ws.query_params.get("room_id"), 64)
        if not room_id:
            await ws.close()
            return
        BUS.add_ws(room_id, ws)
        try:
            while True:
                try:
                    raw = await asyncio.wait_for(ws.receive_text(), timeout=30)
                except asyncio.TimeoutError:
                    await ws.send_json({"ok": True, "type": "ping"})
                    continue
                if raw in {"ping", "pong"}:
                    await ws.send_json({"ok": True, "type": "pong"})
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            BUS.drop_ws(room_id, ws)

    @app.get("/admin/support", response_class=HTMLResponse)
    async def admin_support(request: Request, status: str = "open", q: str = ""):
        staff = require_staff(request)
        ensure_cs_tables(conn)
        status = status if status in {"open", "closed"} else "open"
        rooms = rooms_for_staff(staff["username"], status=status, q=q)
        open_n, unread_n = open_unread_for_staff(staff["username"])
        return render(
            request,
            "admin_support.html",
            rooms=rooms,
            room=None,
            messages=[],
            support_status=status,
            support_q=q,
            unread_n=int(unread_n or 0),
            open_n=int(open_n or 0),
        )

    @app.get("/admin/support/inbox")
    async def admin_support_inbox(request: Request, status: str = "open", q: str = ""):
        staff = require_staff(request)
        ensure_cs_tables(conn)
        rooms = rooms_for_staff(staff["username"], status=status, q=q)
        latest = rooms[0]["updated_at"] if rooms else ""
        open_n, unread_n = open_unread_for_staff(staff["username"])
        return JSONResponse({
            "ok": True,
            "rooms": rooms,
            "latest": latest,
            "unread_n": int(unread_n or 0),
            "open_n": int(open_n or 0),
        })

    @app.get("/admin/support/poll")
    async def admin_support_poll(request: Request, after: str = "", timeout: float = 20):
        staff = require_staff(request)
        ensure_cs_tables(conn)
        timeout = max(1.0, min(float(timeout or 20), 25.0))
        await BUS.wait_inbox(timeout)
        rooms = rooms_for_staff(staff["username"], status="open", q="")
        latest = rooms[0]["updated_at"] if rooms else after
        open_n, unread_n = open_unread_for_staff(staff["username"])
        return JSONResponse({
            "ok": True,
            "rooms": rooms,
            "latest": latest or "",
            "unread_n": int(unread_n or 0),
            "open_n": int(open_n or 0),
        })

    @app.get("/admin/support/{room_id}", response_class=HTMLResponse)
    async def admin_support_room(request: Request, room_id: str):
        staff = require_staff(request)
        room = get_room(conn, room_id)
        if room is None:
            return RedirectResponse("/admin/support", status_code=303)
        ensure_cs_ops_tables(conn)
        if not room_visible_to_agent(conn, room, staff["username"]):
            return RedirectResponse("/admin/support", status_code=303)
        conn.execute("update cs_rooms set unread_staff = 0 where id = ?", (room_id,))
        rooms = rooms_for_staff(staff["username"], status=room["status"], q="")
        open_n, unread_n = open_unread_for_staff(staff["username"])
        return render(
            request,
            "admin_support.html",
            rooms=rooms,
            room=room_dict(room),
            messages=messages_for_staff(room_id),
            support_status=room["status"],
            support_q="",
            unread_n=int(unread_n or 0),
            open_n=int(open_n or 0),
        )

    @app.post("/admin/support/{room_id}/reply")
    async def admin_support_reply(request: Request, room_id: str):
        staff = require_staff(request)
        ctype = (request.headers.get("content-type") or "").lower()
        if "application/json" in ctype:
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            body = _clip(payload.get("body"), 2000)
            image_url = payload.get("image_url") or ""
        else:
            form = await request.form()
            body = _clip(form.get("body"), 2000)
            image_url = form.get("image_url") or ""
        img_body = _normalize_img_body(body, image_url)
        if img_body:
            body = img_body
        room = get_room(conn, room_id)
        if room is None:
            return RedirectResponse("/admin/support", status_code=303)
        if body:
            ensure_cs_ops_tables(conn)
            # visibility: non-admin cannot reply to someone else's room
            if not room_visible_to_agent(conn, room, staff["username"]):
                wants_json = "application/json" in (request.headers.get("accept") or "") or request.headers.get("x-harbor-ajax") == "1"
                if wants_json:
                    return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)
                return RedirectResponse("/admin/support", status_code=303)
            claim_room_if_unassigned(conn, room_id, staff["username"])
            clear_room_ai_mode(conn, room_id, by_user=staff["username"], insert_message_fn=lambda rid, b: insert_message(conn, room_id=rid, role="system", body=b))
            if _is_special_body(body):
                insert_message(
                    conn,
                    room_id=room_id,
                    role="staff",
                    body=body,
                    staff_user=staff["username"],
                    body_original=body,
                    body_zh=body,
                    lang="",
                    translated=0,
                )
            else:
                translate_on = get_setting(conn, "translate_enabled", "1") == "1"
                translate = None
                try:
                    translate = get_translator() if get_translator else None
                except Exception:
                    translate = None
                user_lang = ""
                try:
                    user_lang = room["user_lang"] if "user_lang" in room.keys() else ""
                except Exception:
                    user_lang = ""
                if not user_lang:
                    user_lang = "en"
                prepared = prepare_staff_message(translate, body, user_lang, translate_on)
                insert_message(
                    conn,
                    room_id=room_id,
                    role="staff",
                    body=prepared["body_store"],
                    staff_user=staff["username"],
                    body_original=prepared.get("body_user") or prepared["body_store"],
                    body_zh=prepared["body_zh"],
                    lang=prepared["lang"],
                    translated=prepared["translated"],
                )
        wants_json = "application/json" in (request.headers.get("accept") or "") or request.headers.get("x-harbor-ajax") == "1"
        if wants_json:
            return JSONResponse({"ok": True, "messages": messages_for_staff(room_id)})
        return RedirectResponse(f"/admin/support/{room_id}", status_code=303)

    @app.post("/admin/support/{room_id}/close")
    async def admin_support_close(request: Request, room_id: str):
        require_staff(request)
        conn.execute(
            "update cs_rooms set status='closed', updated_at=? where id=?",
            (utc_now(), room_id),
        )
        BUS.notify_room(room_id)
        BUS.notify_inbox()
        return RedirectResponse("/admin/support", status_code=303)

    @app.get("/api/cs/room/{room_id}")
    async def cs_room_get(request: Request, room_id: str):
        # staff desktop uses cookie auth via require? keep open with staff session OR visitor
        room = get_room(conn, room_id)
        if room is None:
            return JSONResponse({"ok": False, "error": "room"}, status_code=404)
        # Prefer staff view when logged in as staff
        try:
            staff = require_staff(request)
            ensure_cs_ops_tables(conn)
            if not room_visible_to_agent(conn, room, staff["username"]):
                return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)
            conn.execute("update cs_rooms set unread_staff = 0 where id = ?", (room_id,))
            msgs = messages_for_staff(room_id)
        except Exception:
            payload = {"visitor_id": request.query_params.get("visitor_id")}
            if not can_access_room(request, room, payload):
                return JSONResponse({"ok": False, "error": "room"}, status_code=404)
            msgs = messages_for_user(room_id)
        return JSONResponse({"ok": True, "room": room_dict(room), "messages": msgs})



    @app.post("/admin/support/api/typing")
    async def admin_typing(request: Request):
        staff = require_staff(request)
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        room_id = _clip(payload.get("room_id"), 64)
        room = get_room(conn, room_id)
        if room is None:
            return JSONResponse({"ok": False, "error": "room"}, status_code=404)
        ensure_cs_ops_tables(conn)
        if not room_visible_to_agent(conn, room, staff["username"]):
            return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)
        typing_on = bool(payload.get("typing"))
        dn = display_name_of(conn, staff["username"]) or staff["username"]
        if typing_on:
            set_room_typing(room_id, side="staff", name=dn, ttl=6.0, notify=True)
        else:
            clear_room_typing(room_id, side="staff", notify=True)
        return JSONResponse({"ok": True, "typing": get_room_typing(room_id)})

    @app.post("/api/cs/typing")
    async def cs_typing(request: Request):
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        room_id = _clip(payload.get("room_id"), 64)
        room = get_room(conn, room_id)
        if room is None or not can_access_room(request, room, payload):
            return JSONResponse({"ok": False, "error": "room"}, status_code=404)
        typing_on = bool(payload.get("typing"))
        if typing_on:
            set_room_typing(room_id, side="user", name="Customer", ttl=6.0, notify=True)
        else:
            clear_room_typing(room_id, side="user", notify=True)
        return JSONResponse({"ok": True, "typing": get_room_typing(room_id)})

    @app.get("/admin/support/api/room/{room_id}/poll")
    async def admin_room_poll(request: Request, room_id: str, after: int = 0, timeout: float = 20):
        staff = require_staff(request)
        room = get_room(conn, room_id)
        if room is None:
            return JSONResponse({"ok": False, "error": "room"}, status_code=404)
        ensure_cs_ops_tables(conn)
        if not room_visible_to_agent(conn, room, staff["username"]):
            return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)
        timeout = max(1.0, min(float(timeout or 20), 25.0))
        after_id = int(after or 0)
        msgs = messages_for_staff(room_id, after_id=after_id)
        typing = get_room_typing(room_id)
        if msgs:
            return JSONResponse({
                "ok": True,
                "messages": msgs,
                "room": room_dict(get_room(conn, room_id)),
                "typing": typing,
            })
        await BUS.wait_room(room_id, timeout)
        room = get_room(conn, room_id)
        return JSONResponse({
            "ok": True,
            "messages": messages_for_staff(room_id, after_id=after_id),
            "room": room_dict(room) if room else None,
            "typing": get_room_typing(room_id),
        })


    @app.post("/api/cs/upload")
    async def cs_upload(request: Request):
        try:
            data, filename, payload = await _read_upload_payload(request)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc) or "file"}, status_code=400)
        except Exception:
            return JSONResponse({"ok": False, "error": "file"}, status_code=400)
        room_id = _clip(payload.get("room_id"), 64)
        room = get_room(conn, room_id)
        if room is None or not can_access_room(request, room, payload):
            return JSONResponse({"ok": False, "error": "room"}, status_code=404)
        try:
            url = save_cs_image_bytes(data, filename)
        except ValueError as exc:
            code = 400
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=code)
        except Exception:
            return JSONResponse({"ok": False, "error": "save"}, status_code=500)
        return JSONResponse({"ok": True, "url": url})

    @app.post("/admin/support/api/upload")
    async def admin_cs_upload(request: Request):
        require_staff(request)
        try:
            data, filename, _payload = await _read_upload_payload(request)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc) or "file"}, status_code=400)
        except Exception:
            return JSONResponse({"ok": False, "error": "file"}, status_code=400)
        try:
            url = save_cs_image_bytes(data, filename)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        except Exception:
            return JSONResponse({"ok": False, "error": "save"}, status_code=500)
        return JSONResponse({"ok": True, "url": url})

    @app.get("/admin/support/api/stickers")
    async def cs_stickers(request: Request):
        require_staff(request)
        return JSONResponse({"ok": True, "items": list_stickers(conn, enabled_only=True)})

    @app.get("/api/cs/orders")
    async def cs_visitor_orders(request: Request, room_id: str = ""):
        """Visitor-facing order list for chat sheets (room + visitor auth)."""
        ensure_cs_ops_tables(conn)
        room = get_room(conn, room_id)
        payload = {"visitor_id": request.query_params.get("visitor_id")}
        if room is None or not can_access_room(request, room, payload):
            return JSONResponse({"ok": False, "error": "room"}, status_code=404)
        email = (room["email"] or "").strip().lower()
        try:
            be = (buyer_email(request) or "").strip().lower()
            if be:
                email = be
        except Exception:
            pass
        raw = orders_for_email(conn, email, limit=20) if email else []
        out = []
        for o in raw:
            oid = o.get("id")
            try:
                items = _order_line_titles(conn, int(oid), limit=4) if oid is not None else []
            except Exception:
                items = []
            out.append(
                {
                    "id": oid,
                    "submit_id": o.get("submit_id") or "",
                    "status": o.get("status") or "",
                    "currency": o.get("currency") or "",
                    "due_cents": int(o.get("due_cents") or 0),
                    "items": items,
                    "created_at": o.get("created_at") or "",
                    "tracking": o.get("tracking") or "",
                }
            )
        return JSONResponse({"ok": True, "orders": out, "email": email})

    @app.get("/api/cs/stickers")
    async def cs_stickers_public(request: Request):
        # H5 can show the same pack
        ensure_cs_ops_tables(conn)
        return JSONResponse({"ok": True, "items": list_stickers(conn, enabled_only=True)})

    @app.get("/admin/support/api/me")
    async def cs_me(request: Request):
        staff = require_staff(request)
        ensure_cs_ops_tables(conn)
        return JSONResponse({"ok": True, "agent": agent_dict(conn, staff["username"]), "settings": all_settings(conn)})

    @app.post("/admin/support/api/status")
    async def cs_set_status(request: Request):
        staff = require_staff(request)
        try:
            payload = await request.json()
        except Exception:
            form = await request.form()
            payload = dict(form)
        status = _clip(payload.get("status"), 16) or STATUS_ONLINE
        note = _clip(payload.get("note"), 120)
        agent = set_agent_status(conn, staff["username"], status, note, now=utc_now())
        return JSONResponse({"ok": True, "agent": agent})

    @app.get("/admin/support/api/agents")
    async def cs_agents(request: Request):
        require_staff(request)
        return JSONResponse({"ok": True, "agents": list_cs_agents(conn)})

    @app.get("/admin/support/api/canned")
    async def cs_canned(request: Request):
        require_staff(request)
        return JSONResponse({"ok": True, "items": list_canned(conn, enabled_only=True)})

    @app.get("/admin/support/api/orders")
    async def cs_orders(request: Request, room_id: str = "", email: str = ""):
        require_staff(request)
        ensure_cs_ops_tables(conn)
        if get_setting(conn, "show_orders", "1") != "1":
            return JSONResponse({"ok": True, "orders": []})
        em = _clip(email, 120).lower()
        if room_id and not em:
            room = get_room(conn, room_id)
            if room is not None:
                em = (room["email"] or "").lower()
        return JSONResponse({"ok": True, "orders": orders_for_email(conn, em)})

    @app.get("/admin/support/api/orders/{order_id}")
    async def cs_order_one(request: Request, order_id: int):
        require_staff(request)
        detail = order_detail(conn, order_id)
        if not detail:
            return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
        safe = {k: detail[k] for k in detail.keys()}
        return JSONResponse({"ok": True, "order": safe})


    @app.get("/admin/support/api/product/{sku}")
    async def cs_product_detail(request: Request, sku: str):
        require_staff(request)
        ensure_cs_ops_tables(conn)
        detail = product_detail_for_cs(conn, sku)
        if not detail:
            return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
        return JSONResponse({"ok": True, "product": detail})

    @app.get("/admin/support/api/product-search")
    async def cs_product_search(request: Request, q: str = ""):
        require_staff(request)
        ensure_cs_ops_tables(conn)
        items = cs_search_items(conn, q)
        return JSONResponse({"ok": True, "items": items})

    @app.get("/admin/support/api/catalog")
    async def cs_catalog(request: Request):
        require_staff(request)
        return JSONResponse({"ok": True, "items": cs_catalog_slim(conn)})

    @app.get("/api/cs/product/{sku}")
    async def cs_public_product(sku: str, lang: str = ""):
        detail = product_for_visitor(conn, sku, lang or "en")
        if not detail:
            return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
        return JSONResponse({"ok": True, "product": detail})

    @app.post("/admin/support/api/transfer")
    async def cs_transfer(request: Request):
        staff = require_staff(request)
        try:
            payload = await request.json()
        except Exception:
            form = await request.form()
            payload = dict(form)
        room_id = _clip(payload.get("room_id"), 64)
        to_username = _clip(payload.get("to_username") or payload.get("to"), 64)
        room = get_room(conn, room_id)
        if room is None:
            return JSONResponse({"ok": False, "error": "room"}, status_code=404)
        ensure_cs_ops_tables(conn)
        if not room_visible_to_agent(conn, room, staff["username"]) and not staff_is_admin(conn, staff["username"]):
            return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)

        def _sys(rid, body_sys):
            insert_message(conn, room_id=rid, role="system", body=body_sys)

        try:
            result = transfer_room(conn, room_id, staff["username"], to_username, _sys)
            clear_room_ai_mode(conn, room_id, silent=True)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc) or "transfer"}, status_code=400)
        BUS.notify_room(room_id)
        BUS.notify_inbox()
        room2 = get_room(conn, room_id)
        return JSONResponse({
            "ok": True,
            "assignee": result.get("assignee"),
            "prev_assignee": result.get("prev_assignee"),
            "room": room_dict(room2) if room2 else None,
            "messages": messages_for_staff(room_id),
        })


    @app.post("/admin/support/api/to-ai")
    async def cs_to_ai(request: Request):
        staff = require_staff(request)
        try:
            payload = await request.json()
        except Exception:
            form = await request.form()
            payload = dict(form)
        room_id = _clip(payload.get("room_id"), 64)
        room = get_room(conn, room_id)
        if room is None:
            return JSONResponse({"ok": False, "error": "room"}, status_code=404)
        ensure_cs_ops_tables(conn)
        if not room_visible_to_agent(conn, room, staff["username"]) and not staff_is_admin(conn, staff["username"]):
            return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)
        if get_setting(conn, "ai_enabled", "1") != "1":
            return JSONResponse({"ok": False, "error": "ai_disabled"}, status_code=400)

        def _sys(rid, body_sys):
            insert_message(conn, room_id=rid, role="system", body=body_sys)

        try:
            transfer_room_to_ai(conn, room_id, staff["username"], _sys)
        except ValueError as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
        room2 = get_room(conn, room_id)
        return JSONResponse({
            "ok": True,
            "room": room_dict(room2) if room2 else None,
            "messages": messages_for_staff(room_id),
        })

    @app.get("/admin/cs", response_class=HTMLResponse)
    async def admin_cs_page(request: Request):
        staff = require_staff(request)
        from shop.staff import is_admin_role
        ensure_cs_ops_tables(conn)
        return render(
            request,
            "admin_cs.html",
            settings=all_settings(conn),
            agents=list_cs_agents(conn),
            canned=list_canned(conn),
            stickers=list_stickers(conn, enabled_only=False),
            status_labels=STATUS_LABELS_ZH,
            is_admin_role=is_admin_role(staff),
        )

    @app.post("/admin/cs/settings")
    async def admin_cs_settings_save(request: Request):
        staff = require_staff(request)
        from shop.staff import is_admin_role
        if not is_admin_role(staff):
            return RedirectResponse("/admin/cs?flash=forbidden", status_code=303)
        form = await request.form()
        for key in ("translate_enabled", "show_ip_geo", "show_orders", "require_cs_account", "ai_enabled", "ai_only_when_offline", "assign_only_mine", "auto_reassign_when_away"):
            set_setting(conn, key, "1" if form.get(key) in ("1", "on", "true", "yes") else "0")
        if form.get("ai_name") is not None:
            set_setting(conn, "ai_name", _clip(form.get("ai_name"), 40) or "Harbor")
        if form.get("ai_persona") is not None:
            set_setting(conn, "ai_persona", _clip(form.get("ai_persona"), 2000))
        if form.get("ai_handoff_keywords") is not None:
            set_setting(conn, "ai_handoff_keywords", _clip(form.get("ai_handoff_keywords"), 400))
        return RedirectResponse("/admin/cs?flash=saved", status_code=303)

    @app.post("/admin/cs/agents/{username}")
    async def admin_cs_agent_save(request: Request, username: str):
        staff = require_staff(request)
        from shop.staff import is_admin_role, clean_username
        if not is_admin_role(staff):
            return RedirectResponse("/admin/cs?flash=forbidden", status_code=303)
        form = await request.form()
        name = clean_username(username)
        update_agent_profile(
            conn,
            name,
            display_name=str(form.get("display_name") or ""),
            title=str(form.get("title") or ""),
            avatar_url=str(form.get("avatar_url") or ""),
            can_cs=1 if form.get("can_cs") in ("1", "on", "true", "yes") else 0,
        )
        return RedirectResponse("/admin/cs?flash=agent_saved", status_code=303)

    @app.post("/admin/cs/canned")
    async def admin_cs_canned_add(request: Request):
        staff = require_staff(request)
        from shop.staff import is_admin_role
        if not is_admin_role(staff):
            return RedirectResponse("/admin/cs?flash=forbidden", status_code=303)
        form = await request.form()
        ensure_cs_ops_tables(conn)
        title = _clip(form.get("title"), 80)
        body_zh = _clip(form.get("body_zh"), 2000)
        if title and body_zh:
            conn.execute(
                "insert into cs_canned (category, title, body_zh, enabled, sort_n) values (?,?,?,1,?)",
                (_clip(form.get("category") or "通用", 40), title, body_zh, int(form.get("sort_n") or 0)),
            )
        return RedirectResponse("/admin/cs?flash=canned_added", status_code=303)

    @app.post("/admin/cs/canned/{cid}/toggle")
    async def admin_cs_canned_toggle(request: Request, cid: int):
        staff = require_staff(request)
        from shop.staff import is_admin_role
        if not is_admin_role(staff):
            return RedirectResponse("/admin/cs?flash=forbidden", status_code=303)
        row = conn.execute("select enabled from cs_canned where id=?", (cid,)).fetchone()
        if row:
            conn.execute("update cs_canned set enabled=? where id=?", (0 if row["enabled"] else 1, cid))
        return RedirectResponse("/admin/cs?flash=canned_toggled", status_code=303)

