"""Admin money helpers: dollar form fields <-> cents storage."""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


def dollars_to_cents(raw, *, allow_zero=False) -> int | None:
    text = str(raw if raw is not None else "").strip().replace(",", "")
    if not text:
        return None
    try:
        val = Decimal(text)
    except InvalidOperation:
        return None
    cents = int((val * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if cents < 0:
        return None
    if cents == 0 and not allow_zero:
        return None
    return cents


def cents_to_dollars_str(cents) -> str:
    try:
        n = int(cents or 0)
    except (TypeError, ValueError):
        n = 0
    return f"{n / 100:.2f}"


def format_usd(cents) -> str:
    try:
        n = int(cents or 0)
    except (TypeError, ValueError):
        n = 0
    return f"${n / 100:.2f}"
