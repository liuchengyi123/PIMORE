from shop.pricing import quote


def test_japan_example_locks_4200_yen():
    result = quote(
        merchandise_cents=4000,
        tiers=[(3000, 400), (6000, 800)],
        coupon_cents=300,
        coupon_threshold_cents=2000,
        free_shipping_cents=3900,
        shipping_cents=700,
        balance_cents=500,
        use_balance=True,
        units_per_usd=150,
        minor_units=0,
    )
    assert result.discount_cents == 400
    assert result.coupon_cents == 300
    assert result.shipping_cents == 0
    assert result.balance_cents == 500
    assert result.due_cents == 2800
    assert result.due_local == 4200


def test_japan_under_threshold_adds_7_dollars_shipping():
    result = quote(
        merchandise_cents=2500,
        tiers=[(3000, 400)],
        coupon_cents=0,
        coupon_threshold_cents=2000,
        free_shipping_cents=3900,
        shipping_cents=700,
        balance_cents=0,
        use_balance=False,
        units_per_usd=150,
        minor_units=0,
    )
    assert result.shipping_cents == 700
    assert result.due_cents == 3200
    assert result.due_local == 4800


def test_highest_tier_only_and_balance_cannot_pay_shipping():
    result = quote(
        merchandise_cents=6000,
        tiers=[(3000, 400), (6000, 800)],
        coupon_cents=0,
        coupon_threshold_cents=0,
        free_shipping_cents=3900,
        shipping_cents=700,
        balance_cents=100000,
        use_balance=True,
        units_per_usd=1,
        minor_units=2,
    )
    assert result.discount_cents == 800
    assert result.balance_cents == 5200
    assert result.due_cents == 0
