"""How many units to make for the next drop.

First drop: a flat baseline per piece (default 30), so you learn without
over-committing cash.

After that, per category (hoodie, t-shirt, sweatshirt, sweatpants):

* Demand per piece = units sold per piece in recent launched drops, the newest
  weighted most (60/30/10).
* A sold-out piece hid demand, since nobody can buy what isn't there, so its
  sales are scaled up by the stockout uplift (default 1.4).
* Plan = demand + a 10% buffer, rounded to 5, never under 10.
* The size split blends your real sales by size with a standard curve, leaning
  more on your own data as it grows.

The minimum order quantity (MOQ) from your manufacturer is checked last.
"""

from __future__ import annotations

from dataclasses import dataclass, field

CATEGORIES = ("hoodie", "t-shirt", "sweatshirt", "sweatpants")
SIZES = ("XS", "S", "M", "L", "XL", "XXL")
DEFAULT_SIZE_CURVE = {"XS": 0.07, "S": 0.21, "M": 0.31, "L": 0.25, "XL": 0.12, "XXL": 0.04}
RECENCY_WEIGHTS = (0.6, 0.3, 0.1)


@dataclass(frozen=True)
class HistPiece:
    category: str
    units_made: int
    units_sold: int
    sold_by_size: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class HistDrop:
    name: str
    pieces: tuple[HistPiece, ...]


@dataclass(frozen=True)
class PlanSettings:
    baseline_units: int = 30
    buffer: float = 0.10
    stockout_uplift: float = 1.4
    sold_out_at: float = 0.95
    min_units: int = 10
    min_order_qty: int = 0


@dataclass(frozen=True)
class CategoryPlan:
    category: str
    units_per_piece: int
    sell_through: float | None
    reason: str
    by_size: dict[str, int]
    below_moq: bool


@dataclass(frozen=True)
class Plan:
    first_drop: bool
    based_on: list[str]
    size_curve: dict[str, float]
    size_data_weight: float
    categories: list[CategoryPlan]


def round5(x: float) -> int:
    return int(round(x / 5.0) * 5)


def split_sizes(units: int, curve: dict[str, float]) -> dict[str, int]:
    """Split units across sizes, largest-remainder so the parts add up exactly."""
    raw = {s: units * curve.get(s, 0) for s in SIZES}
    out = {s: int(v) for s, v in raw.items()}
    short = units - sum(out.values())
    for s in sorted(raw, key=lambda k: raw[k] - out[k], reverse=True)[:short]:
        out[s] += 1
    return {s: n for s, n in out.items() if n > 0}


def size_curve(history: list[HistDrop]) -> tuple[dict[str, float], float]:
    totals: dict[str, int] = {}
    for d in history:
        for p in d.pieces:
            for s, n in p.sold_by_size.items():
                if s in SIZES and n > 0:
                    totals[s] = totals.get(s, 0) + n
    n = sum(totals.values())
    weight = min(0.8, n / 150) if n else 0.0
    curve = {s: (1 - weight) * DEFAULT_SIZE_CURVE[s] + weight * (totals.get(s, 0) / n if n else 0) for s in SIZES}
    norm = sum(curve.values())
    return {s: round(v / norm, 4) for s, v in curve.items()}, round(weight, 3)


def plan_next_drop(history: list[HistDrop], settings: PlanSettings | None = None) -> Plan:
    """`history` must be launched drops with sales entered, newest first."""
    cfg = settings or PlanSettings()
    usable = [d for d in history if any(p.units_made > 0 for p in d.pieces)][: len(RECENCY_WEIGHTS)]
    curve, weight = size_curve(usable)

    if not usable:
        units = max(cfg.baseline_units, cfg.min_units)
        return Plan(
            first_drop=True,
            based_on=[],
            size_curve=curve,
            size_data_weight=0.0,
            categories=[
                CategoryPlan(
                    category=c,
                    units_per_piece=units,
                    sell_through=None,
                    reason="First drop: start at the baseline and learn what sells.",
                    by_size=split_sizes(units, curve),
                    below_moq=units < cfg.min_order_qty,
                )
                for c in CATEGORIES
            ],
        )

    stats: dict[str, dict[str, float]] = {}
    for w, d in zip(RECENCY_WEIGHTS, usable):
        per_cat: dict[str, list[HistPiece]] = {}
        for p in d.pieces:
            if p.units_made > 0:
                per_cat.setdefault(p.category, []).append(p)
        for cat, ps in per_cat.items():
            made = sum(p.units_made for p in ps)
            sold = sum(min(p.units_sold, p.units_made) for p in ps)
            st = sold / made
            demand = sum(
                p.units_sold * (cfg.stockout_uplift if p.units_sold >= p.units_made * cfg.sold_out_at else 1.0)
                for p in ps
            ) / len(ps)
            s = stats.setdefault(cat, {"w": 0.0, "demand": 0.0, "st": 0.0})
            s["w"] += w
            s["demand"] += w * demand
            s["st"] += w * st

    plans = []
    for cat in CATEGORIES:
        s = stats.get(cat)
        if not s:
            units = cfg.baseline_units
            plans.append(
                CategoryPlan(cat, units, None, "No sales history for this item yet, so it starts at the baseline.",
                             split_sizes(units, curve), units < cfg.min_order_qty)
            )
            continue
        demand, st = s["demand"] / s["w"], s["st"] / s["w"]
        units = max(cfg.min_units, round5(demand * (1 + cfg.buffer)))
        pct = f"{st:.0%}"
        if st >= cfg.sold_out_at:
            reason = f"Sold out ({pct}). Demand was higher than stock, so the plan goes up."
        elif st >= 0.7:
            reason = f"Sold {pct}. Healthy: plan close to what sold, plus a small buffer."
        elif st >= 0.5:
            reason = f"Sold {pct}. Plan to what actually sold."
        else:
            reason = f"Only {pct} sold. Cut back so stock doesn't sit."
        plans.append(CategoryPlan(cat, units, round(st, 4), reason, split_sizes(units, curve),
                                  units < cfg.min_order_qty))

    return Plan(False, [d.name for d in usable], curve, weight, plans)
