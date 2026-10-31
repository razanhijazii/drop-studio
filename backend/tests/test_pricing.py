import pytest

from app.services.pricing import PricingInput, clean_price, suggest_price


def test_clean_price_steps():
    assert clean_price(63) == 65
    assert clean_price(62) == 60
    assert clean_price(104) == 100
    assert clean_price(106) == 110
    assert clean_price(61, up=True) == 65


def test_cost_only_hits_target_margin():
    r = suggest_price(PricingInput(unit_cost=24, category="hoodie"))
    assert r.cost_target == 80
    assert r.recommended == 80
    assert r.margin_at_recommended == pytest.approx(0.70)
    assert any("No competitor prices" in w for w in r.warnings)


def test_market_above_cost_target_follows_market():
    r = suggest_price(PricingInput(unit_cost=20, category="hoodie", competitor_prices=(100, 120, 140)))
    # median 120 x 0.9 = 108 -> 110
    assert r.market_median == 120
    assert r.recommended == 110
    assert r.margin_at_recommended > 0.8


def test_cost_above_market_is_capped_and_warned():
    r = suggest_price(PricingInput(unit_cost=60, category="hoodie", competitor_prices=(90, 100, 110)))
    assert r.cost_target == 200
    assert r.recommended <= 140  # floor 133.33 -> 140, above market high of 105
    assert r.recommended >= r.floor
    assert any("above what comparable brands charge" in w for w in r.warnings)


def test_never_below_floor():
    r = suggest_price(PricingInput(unit_cost=40, category="t-shirt", competitor_prices=(30, 35, 40),
                                   past_sell_through=0.2))
    assert r.recommended >= r.floor


def test_demand_nudges():
    base = suggest_price(PricingInput(unit_cost=24, category="hoodie"))
    hot = suggest_price(PricingInput(unit_cost=24, category="hoodie", past_sell_through=1.0))
    slow = suggest_price(PricingInput(unit_cost=24, category="hoodie", past_sell_through=0.3))
    assert hot.recommended > base.recommended
    assert slow.recommended <= base.recommended
    assert any("smaller run" in w for w in slow.warnings)


def test_discount_warning_and_current_price():
    r = suggest_price(PricingInput(unit_cost=20, category="hoodie", past_discount_rate=0.25, current_price=40))
    assert any("below list price" in w for w in r.warnings)
    assert any("below the floor" in w for w in r.warnings)
    assert r.current_margin == 0.5


def test_bad_inputs():
    with pytest.raises(ValueError):
        suggest_price(PricingInput(unit_cost=0, category="hoodie"))
    with pytest.raises(ValueError):
        suggest_price(PricingInput(unit_cost=10, category="hoodie", min_margin=0.8, target_margin=0.6))
