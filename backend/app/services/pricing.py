"""Price suggestions for a piece.

The suggestion combines three things, in this order:

1. Cost. The floor is the lowest price that keeps the minimum margin; the
   cost-based target is the price at the target margin. Premium DTC basics
   typically run 65-80% gross margin, so the defaults are 55% floor, 70% target.
2. Market. If you've logged competitor prices for the category, the anchor is
   their median times your market position (0.9 = a little under the brands
   you benchmark against). The ceiling is their upper quartile.
3. Demand. Past sell-through for the category nudges the price: sold-out
   items can carry more, slow ones get flagged. A slow seller is flagged
   for smaller runs rather than heavy discounting, since discounting wears
   down a premium brand.

Prices are rounded to clean numbers (5s under 100, 10s above) the way premium
brands price, and never below the floor.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import median


@dataclass(frozen=True)
class PricingInput:
    unit_cost: float
    category: str
    target_margin: float = 0.70
    min_margin: float = 0.55
    market_position: float = 0.90
    competitor_prices: tuple[float, ...] = ()
    past_sell_through: float | None = None  # weighted, for this category
    past_discount_rate: float | None = None
    current_price: float | None = None


@dataclass(frozen=True)
class PricingResult:
    recommended: float
    floor: float
    cost_target: float
    market_low: float | None
    market_median: float | None
    market_high: float | None
    margin_at_recommended: float
    markup: float
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    current_margin: float | None = None


def plural(category: str) -> str:
    return category if category.endswith("s") else category + "s"


def clean_price(x: float, *, up: bool = False) -> float:
    step = 5 if x < 100 else 10
    f = math.ceil if up else round
    return float(f(x / step) * step)


def _quartiles(values: list[float]) -> tuple[float, float, float]:
    v = sorted(values)
    if len(v) == 1:
        return v[0], v[0], v[0]
    # Inclusive linear interpolation, the same as Excel's QUARTILE.INC.
    def q(p: float) -> float:
        idx = p * (len(v) - 1)
        lo, hi = math.floor(idx), math.ceil(idx)
        return v[lo] + (v[hi] - v[lo]) * (idx - lo)

    return q(0.25), median(v), q(0.75)


def suggest_price(inp: PricingInput) -> PricingResult:
    if inp.unit_cost <= 0:
        raise ValueError("unit_cost must be greater than zero")
    if not 0 < inp.min_margin <= inp.target_margin < 1:
        raise ValueError("margins must satisfy 0 < min_margin <= target_margin < 1")

    reasons: list[str] = []
    warnings: list[str] = []

    floor = inp.unit_cost / (1 - inp.min_margin)
    cost_target = inp.unit_cost / (1 - inp.target_margin)
    reasons.append(
        f"At a cost of {inp.unit_cost:.2f}, a {inp.target_margin:.0%} margin needs {cost_target:.2f}; "
        f"anything under {floor:.2f} drops below your {inp.min_margin:.0%} minimum."
    )

    low = mid = high = None
    if inp.competitor_prices:
        low, mid, high = _quartiles(list(inp.competitor_prices))
        anchor = mid * inp.market_position
        reasons.append(
            f"Brands you benchmark sell {plural(inp.category)} around {mid:.0f} (range {low:.0f}–{high:.0f}); "
            f"your position puts you near {anchor:.0f}."
        )
        if cost_target <= anchor:
            base = anchor
            reasons.append("The market supports more than your cost target, so the price follows the market.")
        else:
            base = min(cost_target, high)
            if cost_target > high:
                warnings.append(
                    f"Your cost target ({cost_target:.0f}) is above what comparable brands charge ({high:.0f}). "
                    "Lower the unit cost or accept a thinner margin on this piece."
                )
        if len(inp.competitor_prices) < 3:
            warnings.append("Fewer than 3 competitor prices logged for this category; add more for a steadier market read.")
    else:
        base = cost_target
        warnings.append(f"No competitor prices logged for {plural(inp.category)} yet, so this is based on cost alone.")

    st = inp.past_sell_through
    if st is not None:
        if st >= 0.95:
            base *= 1.08
            reasons.append(f"Last drops sold out ({st:.0%}): demand can carry about 8% more.")
        elif st >= 0.80:
            base *= 1.04
            reasons.append(f"Strong sell-through ({st:.0%}): room for a small increase.")
        elif st < 0.50:
            base *= 0.95
            reasons.append(f"Only {st:.0%} sold last time: priced slightly lower.")
            warnings.append("Slow sellers usually need a smaller run more than a lower price. Check the stock plan.")
    if inp.past_discount_rate is not None and inp.past_discount_rate > 0.15:
        warnings.append(
            f"You've been selling about {inp.past_discount_rate:.0%} below list price. "
            "Frequent discounts teach customers to wait; fewer units protects the price better."
        )

    recommended = max(clean_price(base), clean_price(floor, up=True))
    margin = 1 - inp.unit_cost / recommended

    current_margin = None
    if inp.current_price:
        current_margin = round(1 - inp.unit_cost / inp.current_price, 4)
        if inp.current_price < floor:
            warnings.append(f"Your current price ({inp.current_price:.2f}) is below the floor.")

    return PricingResult(
        recommended=recommended,
        floor=round(floor, 2),
        cost_target=round(cost_target, 2),
        market_low=round(low, 2) if low is not None else None,
        market_median=round(mid, 2) if mid is not None else None,
        market_high=round(high, 2) if high is not None else None,
        margin_at_recommended=round(margin, 4),
        markup=round(recommended / inp.unit_cost, 2),
        reasons=reasons,
        warnings=warnings,
        current_margin=current_margin,
    )
