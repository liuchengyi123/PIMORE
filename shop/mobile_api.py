"""JSON catalog endpoints for Harbor Android / mobile clients.

Mounted from create_app; reuses present_card / present / catalog helpers.
Does not change SSR HTML routes.
"""

from __future__ import annotations

import hashlib
import secrets
from typing import Callable, Iterable, Optional

from fastapi import Request
from fastapi.responses import JSONResponse


# Android chip labels (MockCatalog) <-> shop CATEGORIES keys.
LABEL_FOR = {
    "kitchen": "Kitchen",
    "cleaning": "Cleaning",
    "storage": "Storage",
    "pet": "Pet",
    "tableware": "Tableware",
    "paper": "Paper",
    "daily": "Home",
    "personal": "Bath",
    "beauty": "Bath",
    "makeup": "Bath",
    "textile": "Home",
    "decor": "Home",
    "appliance": "Home",
    "hardware": "Home",
    "office": "Paper",
    "party": "Paper",
}

# Incoming ?category= from the app (chip / department title) -> DB keys.
FILTER_KEYS = {
    "kitchen": ("kitchen",),
    "cleaning": ("cleaning",),
    "storage": ("storage",),
    "pet": ("pet",),
    "tableware": ("tableware",),
    "paper": ("paper", "office", "party"),
    "bath": ("personal", "beauty", "makeup"),
    "home": ("daily", "textile", "decor", "appliance", "hardware"),
    "home basics": ("daily", "textile", "decor", "appliance", "hardware"),
    "daily": ("daily",),
    "personal": ("personal",),
    "beauty": ("beauty",),
    "office": ("office",),
}

_SOCIAL_PROVIDERS = {
    "google",
    "facebook",
    "fb",
    "meta",
    "x",
    "twitter",
    "instagram",
    "ig",
    "apple",
}


def _category_keys(requested: Optional[str]) -> Optional[tuple]:
    if requested is None:
        return None
    raw = str(requested).strip()
    if not raw or raw.casefold() in {"for you", "all", "recommended", "*"}:
        return None
    key = raw.casefold()
    if key in FILTER_KEYS:
        return FILTER_KEYS[key]
    return (key,)


def _categories_for(db_category: str) -> list:
    cat = (db_category or "").strip()
    labels = []
    if cat:
        labels.append(cat)
        pretty = LABEL_FOR.get(cat)
        if pretty and pretty not in labels:
            labels.append(pretty)
    return labels


def _interest(item: dict) -> str:
    left = item.get("only_left")
    try:
        left_n = int(left) if left not in (None, "", False) else 0
    except (TypeError, ValueError):
        left_n = 0
    if left_n > 0:
        return f"Only {left_n} left"
    try:
        heat = int(item.get("heat") or 0)
    except (TypeError, ValueError):
        heat = 0
    if heat > 0:
        return f"关注热度 · {heat}"
    stock = item.get("stock")
    try:
        if stock is not None and int(stock) <= 0:
            return "Out of stock"
    except (TypeError, ValueError):
        pass
    return "In stock"


def product_json(item: dict, *, detail: bool = False) -> dict:
    """Map present_card / present() dict to Android CatalogRepository fields."""
    sku = str(item.get("sku") or item.get("id") or "")
    title = str(item.get("name") or item.get("title") or sku)
    cents = item.get("price_cents")
    try:
        cents = int(cents or 0)
    except (TypeError, ValueError):
        cents = 0
    image = item.get("image") or item.get("image_url") or ""
    images = []
    for key in ("images", "detail_images", "gallery"):
        node = item.get(key) or []
        if isinstance(node, list):
            for url in node:
                if url and url not in images:
                    images.append(url)
    if image and image not in images:
        images.insert(0, image)
    elif images and not image:
        image = images[0]
    cats = _categories_for(str(item.get("category") or ""))
    payload = {
        "id": sku,
        "sku": sku,
        "title": title,
        "name": title,
        "priceCents": cents,
        "price_cents": cents,
        "price": round(cents / 100.0, 2) if cents else 0,
        "category": cats[1] if len(cats) > 1 else (cats[0] if cats else ""),
        "categories": cats,
        "image": image,
        "imageUrl": image,
        "images": images,
        "interest": _interest(item),
        "stock": item.get("stock"),
        "shipping": "Free shipping" if item.get("free_shipping") else (item.get("shipping") or "Shipping calculated at checkout"),
        "stockLabel": "In stock" if int(item.get("stock") or 0) > 0 else "Out of stock",
    }
    if detail:
        payload["description"] = item.get("description") or ""
        payload["specs"] = item.get("specs") or {}
        payload["delivery"] = item.get("delivery") or "Estimated delivery 5-9 days"
        offers = item.get("offers") or []
        skus = []
        for idx, offer in enumerate(offers):
            if not isinstance(offer, dict):
                continue
            oid = str(offer.get("id") or offer.get("sku") or f"{sku}-{idx}")
            label = str(offer.get("name") or offer.get("label") or offer.get("title") or f"Option {idx + 1}")
            oimg = offer.get("image") or offer.get("image_url") or image
            skus.append({"id": oid, "label": label, "image": oimg, "imageUrl": oimg})
        if not skus:
            skus = [
                {"id": f"{sku}-0", "label": "Standard", "image": image, "imageUrl": image},
                {"id": f"{sku}-1", "label": "Compact", "image": image, "imageUrl": image},
            ]
        payload["skus"] = skus
    return payload


def _norm_provider(raw: str) -> str:
    key = (raw or "").strip().casefold()
    if key in {"fb", "meta"}:
        return "facebook"
    if key in {"twitter"}:
        return "x"
    if key in {"ig"}:
        return "instagram"
    return key


def _default_display_name(provider: str) -> str:
    return {
        "google": "Google user",
        "facebook": "Facebook user",
        "x": "X user",
        "instagram": "Instagram user",
        "apple": "Apple user",
    }.get(provider, "Harbor user")


def _ensure_social_tables(conn) -> None:
    conn.execute(
        """
        create table if not exists social_identities (
            provider text not null,
            subject text not null,
            email text not null,
            display_name text not null default '',
            updated_at text not null default (datetime('now')),
            primary key (provider, subject)
        )
        """
    )
    try:
        conn.execute(
            "alter table accounts add column display_name text not null default ''"
        )
    except Exception:
        pass


def _subject_from_body(body: dict, provider: str) -> str:
    for key in ("userID", "userId", "user_id", "subject", "sub", "id"):
        value = body.get(key)
        if value not in (None, ""):
            return str(value).strip()
    token = (
        body.get("idToken")
        or body.get("id_token")
        or body.get("accessToken")
        or body.get("access_token")
        or body.get("token")
        or ""
    )
    token = str(token).strip()
    if token:
        digest = hashlib.sha256(f"{provider}:{token}".encode("utf-8")).hexdigest()[:24]
        return digest
    return secrets.token_hex(12)


def _email_from_body(body: dict, provider: str, subject: str) -> str:
    email = str(body.get("email") or "").strip().lower()
    if "@" in email and not email.startswith("@") and not email.endswith("@"):
        return email
    safe_subject = "".join(ch if ch.isalnum() else "-" for ch in subject)[:48] or "user"
    return f"{provider}.{safe_subject}@social.harbor.local"


def _display_name_from_body(body: dict, provider: str) -> str:
    for key in ("displayName", "display_name", "name", "fullName", "full_name"):
        value = body.get(key)
        if value not in (None, ""):
            return str(value).strip()[:120]
    return _default_display_name(provider)


def _credential_present(body: dict) -> bool:
    for key in (
        "idToken",
        "id_token",
        "accessToken",
        "access_token",
        "token",
        "authorizationCode",
        "authorization_code",
        "code",
        "userID",
        "userId",
        "user_id",
        "subject",
        "sub",
    ):
        if body.get(key) not in (None, ""):
            return True
    return False


def mount_mobile_api(
    app,
    *,
    view: Callable,
    catalog_rows: Callable,
    catalog_index: Callable,
    present_card: Callable,
    present: Callable,
    home_feed_cards: Callable,
    ui: dict,
):
    def _filter_rows(rows: Iterable[dict], category: Optional[str]):
        keys = _category_keys(category)
        if keys is None:
            return list(rows)
        wanted = set(keys)
        return [row for row in rows if str(row.get("category") or "") in wanted]

    @app.get("/api/legal")
    def api_legal(request: Request):
        """Canonical compliance URLs for native apps + H5."""
        base = str(request.base_url).rstrip("/")
        # Prefer public site host when behind proxy
        host = request.headers.get("x-forwarded-host") or request.headers.get("host")
        proto = request.headers.get("x-forwarded-proto") or request.url.scheme
        if host:
            base = f"{proto}://{host}".rstrip("/")
        return {
            "brand": "Pimo",
            "support_email": "support@linkiip.com",
            "help": f"{base}/help",
            "privacy": f"{base}/policies/privacy",
            "terms": f"{base}/policies/terms",
            "shipping": f"{base}/policies/shipping",
            "contact": f"{base}/contact",
            "account_deletion": f"{base}/help#account-deletion",
        }

    @app.get("/api/home")
    def api_home(request: Request):
        ctx = view(request)
        cards, _more, _tab = home_feed_cards(
            request, ctx, tab="recommended", page=1, page_size=24
        )
        products = [product_json(card) for card in cards]
        copy = (ui.get(ctx.get("lang") or "en") or ui.get("en") or {})
        promo = {
            "eyebrow": copy.get("hero_kicker") or "THIS WEEK",
            "title": copy.get("hero_title") or "Kitchen refresh · up to 30% off",
            "cta": "Shop",
        }
        return JSONResponse(
            {
                "ok": True,
                "promo": promo,
                "products": products,
                "banner": promo,
            }
        )

    @app.get("/api/products")
    def api_products(
        request: Request,
        limit: int = 24,
        offset: int = 0,
        page: int = 0,
        page_size: int = 0,
        category: Optional[str] = None,
    ):
        ctx = view(request)
        # Honor page/page_size in addition to limit/offset (mobile clients use both).
        try:
            page_i = int(page or 0)
        except (TypeError, ValueError):
            page_i = 0
        try:
            page_size_i = int(page_size or 0)
        except (TypeError, ValueError):
            page_size_i = 0
        if page_size_i > 0:
            limit = page_size_i
        if page_i > 0:
            offset = max(0, (page_i - 1) * max(1, int(limit or 24)))
        limit = max(1, min(100, int(limit or 24)))
        offset = max(0, int(offset or 0))
        rows = _filter_rows(catalog_rows(), category)
        stocked = [row for row in rows if int(row.get("stock") or 0) > 0]
        pool = stocked or list(rows)
        slice_rows = pool[offset : offset + limit]
        products = [product_json(present_card(row, ctx)) for row in slice_rows]
        return JSONResponse(
            {
                "ok": True,
                "products": products,
                "items": products,
                "total": len(pool),
                "limit": limit,
                "offset": offset,
                "page": page_i or ((offset // limit) + 1 if limit else 1),
                "page_size": limit,
                "category": category,
            }
        )

    @app.get("/api/products/{sku}")
    def api_product_detail(request: Request, sku: str):
        ctx = view(request)
        row = catalog_index().get(sku)
        if row is None:
            base = sku.split("~", 1)[0]
            row = catalog_index().get(base)
        if row is None or not int(row.get("published") or 0):
            return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
        item = present(row, ctx)
        card = present_card(row, ctx)
        item["heat"] = card.get("heat")
        item["only_left"] = card.get("only_left")
        item["free_shipping"] = card.get("free_shipping")
        detail = product_json(item, detail=True)
        return JSONResponse({"ok": True, "product": detail, **detail})

    @app.post("/api/auth/social")
    async def api_auth_social(request: Request):
        """Accept Android / iOS social payloads and mint a buyer session.

        Android body: provider, idToken?, accessToken?
        iOS body: provider, token, name?, email?, userID
        Provider token verification is deferred until App IDs / secrets are filled;
        clients already fall back to a local session when this route is missing.
        """
        try:
            body = await request.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}

        provider = _norm_provider(str(body.get("provider") or ""))
        if provider not in _SOCIAL_PROVIDERS:
            return JSONResponse(
                {"ok": False, "code": "provider", "message": "Unknown social provider"},
                status_code=400,
            )
        if not _credential_present(body):
            return JSONResponse(
                {"ok": False, "code": "token", "message": "Missing social credential"},
                status_code=400,
            )

        conn = getattr(request.app.state, "db", None)
        if conn is None:
            return JSONResponse(
                {"ok": False, "code": "db", "message": "Database unavailable"},
                status_code=503,
            )

        _ensure_social_tables(conn)
        subject = _subject_from_body(body, provider)
        display_name = _display_name_from_body(body, provider)
        email = _email_from_body(body, provider, subject)

        known = conn.execute(
            "select email, display_name from social_identities where provider = ? and subject = ?",
            (provider, subject),
        ).fetchone()
        if known is not None:
            email = str(known["email"] or email)
            prior_name = str(known["display_name"] or "").strip()
            if prior_name and display_name == _default_display_name(provider):
                display_name = prior_name

        account = conn.execute(
            "select email from accounts where email = ?", (email,)
        ).fetchone()
        if account is None:
            conn.execute(
                "insert into accounts (email, password_hash, referrer_email) values (?, null, null)",
                (email,),
            )
        try:
            conn.execute(
                "update accounts set display_name = ? where email = ?",
                (display_name, email),
            )
        except Exception:
            pass

        conn.execute(
            """
            insert into social_identities (provider, subject, email, display_name, updated_at)
            values (?, ?, ?, ?, datetime('now'))
            on conflict(provider, subject) do update set
                email = excluded.email,
                display_name = excluded.display_name,
                updated_at = excluded.updated_at
            """,
            (provider, subject, email, display_name),
        )

        token = secrets.token_urlsafe(24)
        conn.execute("insert into sessions (token, email) values (?, ?)", (token, email))
        try:
            conn.commit()
        except Exception:
            pass

        user = {
            "email": email,
            "name": display_name,
            "displayName": display_name,
            "provider": provider,
            "userID": subject,
        }
        response = JSONResponse(
            {
                "ok": True,
                "token": token,
                "sessionToken": token,
                "email": email,
                "name": display_name,
                "displayName": display_name,
                "provider": provider,
                "user": user,
                "data": {
                    "token": token,
                    "sessionToken": token,
                    "email": email,
                    "name": display_name,
                    "displayName": display_name,
                    "provider": provider,
                },
            }
        )
        response.set_cookie("buyer_session", token, httponly=True, path="/")
        return response
