"""Active buyer theme for Harbor shopper clients.

One settings row (``buyer_theme``) stores the active pack id. Packs live in
code so every client renders the same tokens. Admin only chooses which pack
is active; it does not edit individual colors.

The JSON shape is the contract for harbor-web and for the native iOS and
Android apps. See ``docs/buyer-theme.md``.
"""

from __future__ import annotations

SETTING_KEY = "buyer_theme"
VERSION = 1
DEFAULT_ID = "coral-market"

# Authored keys. Do not add colors here without bumping VERSION.
TOKEN_KEYS = (
    "color.primary",
    "color.primarySoft",
    "color.page",
    "color.ink",
    "color.muted",
    "color.onPrimary",
    "color.surface",
    "color.sale",
    "color.badge",
)

# Computed from the authored tokens. Clients may ignore these and recompute.
DERIVED_KEYS = (
    "color.primaryHover",
    "color.primaryPressed",
    "color.primaryDisabled",
)

# sRGB byte mix weights. See docs/buyer-theme.md.
HOVER_BLACK = 0.12
PRESSED_BLACK = 0.22
DISABLED_SURFACE = 0.48


class ThemeError(ValueError):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _channels(value: str) -> tuple[int, int, int]:
    text = str(value or "").strip()
    if len(text) != 7 or not text.startswith("#"):
        raise ThemeError(f"bad color {value!r}")
    try:
        return tuple(int(text[i : i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]
    except ValueError as exc:
        raise ThemeError(f"bad color {value!r}") from exc


def _hex(channels: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*channels)


def mix(source: str, target: str, target_weight: float) -> str:
    """Mix two #RRGGBB colors in sRGB byte space. ``target_weight`` is 0–1.

    Half-up rounding. This is the version-1 derivation; do not switch it to
    linear-light without bumping VERSION.
    """
    weight = float(target_weight)
    if weight < 0 or weight > 1:
        raise ThemeError("mix weight out of range")
    left = _channels(source)
    right = _channels(target)
    mixed = []
    for a, b in zip(left, right):
        mixed.append(int(a * (1 - weight) + b * weight + 0.5))
    return _hex((mixed[0], mixed[1], mixed[2]))


def derive(tokens: dict) -> dict:
    primary = tokens["color.primary"]
    surface = tokens["color.surface"]
    return {
        "color.primaryHover": mix(primary, "#000000", HOVER_BLACK),
        "color.primaryPressed": mix(primary, "#000000", PRESSED_BLACK),
        "color.primaryDisabled": mix(primary, surface, DISABLED_SURFACE),
    }


def _pack(pack_id: str, name: str, tokens: dict) -> dict:
    if set(tokens) != set(TOKEN_KEYS):
        raise ThemeError(f"{pack_id} tokens do not match the v1 contract")
    ordered = {key: tokens[key].upper() for key in TOKEN_KEYS}
    for value in ordered.values():
        _channels(value)
    return {"id": pack_id, "name": name, "tokens": ordered}


PACKS = {
    "coral-market": _pack(
        "coral-market",
        "Coral Market",
        {
            # Primary CTAs, selected tab, switches, links, progress, coupon border.
            "color.primary": "#FF6A3D",
            # Selected chip fills, coupon/countdown wells, light badges.
            "color.primarySoft": "#FFD4C4",
            # Page canvas, including the desktop gutters outside the shopper column.
            "color.page": "#FFF4F0",
            # Titles and product names.
            "color.ink": "#2C2623",
            # Secondary text and compare-at / strikethrough prices.
            "color.muted": "#6E5E58",
            # Label on a primary fill (Add to cart, Buy now, Checkout).
            "color.onPrimary": "#FFFFFF",
            # Cards, search and header bars, sheets, tab bar.
            "color.surface": "#FFFFFF",
            # Sale price. Not the button color.
            "color.sale": "#C41E16",
            # Discount badge fill. Not the button color.
            "color.badge": "#9F1239",
        },
    ),
}


def active_id(conn) -> str:
    try:
        row = conn.execute(
            "select value from settings where key = ?",
            (SETTING_KEY,),
        ).fetchone()
    except Exception:
        return DEFAULT_ID
    if row is None:
        return DEFAULT_ID
    found = str(row["value"] or "").strip()
    if found not in PACKS:
        return DEFAULT_ID
    return found


def pack_payload(pack_id: str) -> dict:
    pack = PACKS[pack_id]
    tokens = dict(pack["tokens"])
    return {
        "id": pack["id"],
        "name": pack["name"],
        "tokens": tokens,
        "derived": derive(tokens),
    }


def public_theme(conn) -> dict:
    current = active_id(conn)
    return {
        "ok": True,
        "version": VERSION,
        "activeId": current,
        "pack": pack_payload(current),
        "packs": [{"id": pack["id"], "name": pack["name"]} for pack in PACKS.values()],
    }


def save_active_id(conn, pack_id: str) -> str:
    found = str(pack_id or "").strip()
    if found not in PACKS:
        raise ThemeError("unknown pack")
    conn.execute(
        "insert into settings (key, value) values (?, ?) on conflict(key) do update set value = excluded.value",
        (SETTING_KEY, found),
    )
    return found


def admin_choices(conn) -> list[dict]:
    current = active_id(conn)
    rows = []
    for pack in PACKS.values():
        rows.append(
            {
                "id": pack["id"],
                "name": pack["name"],
                "primary": pack["tokens"]["color.primary"],
                "soft": pack["tokens"]["color.primarySoft"],
                "page": pack["tokens"]["color.page"],
                "sale": pack["tokens"]["color.sale"],
                "selected": pack["id"] == current,
            }
        )
    return rows
