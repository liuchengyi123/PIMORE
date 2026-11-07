from shop.rewards import apply_refund, rebate


def test_self_and_direct_referrer():
    own, direct = rebate(
        base_cents=3300,
        self_rate=0.05,
        direct_rate=0.10,
        referrer="d@x.com",
        buyer="e@x.com",
    )
    assert own == 165
    assert direct == 330


def test_own_link_does_not_pay_twice():
    own, direct = rebate(
        base_cents=3300,
        self_rate=0.05,
        direct_rate=0.10,
        referrer="e@x.com",
        buyer="e@x.com",
    )
    assert (own, direct) == (165, 0)


def test_refund_claws_back_only_available_balance():
    assert apply_refund(rebate_cents=500, available_cents=200) == 0
    assert apply_refund(rebate_cents=500, available_cents=800) == 300
