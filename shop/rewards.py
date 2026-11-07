def rebate(*, base_cents, self_rate, direct_rate, referrer, buyer):
    own = int(base_cents * self_rate + 0.5)
    if referrer and referrer != buyer:
        direct = int(base_cents * direct_rate + 0.5)
    else:
        direct = 0
    return own, direct


def apply_refund(rebate_cents, available_cents):
    return max(0, available_cents - rebate_cents)
