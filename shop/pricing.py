from dataclasses import dataclass


@dataclass(frozen=True)
class Quote:
    discount_cents: int
    coupon_cents: int
    shipping_cents: int
    balance_cents: int
    due_cents: int
    due_local: int


def quote(
    *,
    merchandise_cents,
    tiers,
    coupon_cents,
    coupon_threshold_cents,
    free_shipping_cents,
    shipping_cents,
    balance_cents,
    use_balance,
    units_per_usd,
    minor_units,
    lucky_off_cents=0,
):
    hit = [off for threshold, off in tiers if merchandise_cents >= threshold]
    discount = max(hit) if hit else 0
    coupon = coupon_cents if merchandise_cents >= coupon_threshold_cents else 0
    ship = 0 if merchandise_cents >= free_shipping_cents else shipping_cents
    lucky = max(0, int(lucky_off_cents or 0))
    room = max(0, merchandise_cents - discount - coupon)
    lucky = min(lucky, room)
    discount += lucky
    goods_after = max(0, merchandise_cents - discount - coupon)
    balance = min(balance_cents, goods_after) if use_balance else 0
    due = goods_after + ship - balance
    factor = 10 ** minor_units
    local = int((due * units_per_usd * factor) / 100 + 0.5)
    return Quote(discount, coupon, ship, balance, due, local)
