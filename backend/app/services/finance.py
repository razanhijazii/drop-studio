"""Revenue, profit and cash for each piece, each drop and the whole brand.

Two views of money, because they answer different questions:

* Profit on what you sold: revenue - cost of the units that sold - drop expenses.
  This is the accounting answer: is each sale making money?
* Cash back: revenue - everything you paid to produce - drop expenses.
  This is the survival answer: have you got your money back yet? Unsold stock
  is cash sitting on a shelf, so it's reported separately at cost.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date


def _r(x: float) -> float:
    return round(x + 0.0, 2)


@dataclass(frozen=True)
class SaleLine:
    quantity: int
    unit_price: float
    sold_on: date
    size: str | None = None
    channel: str = "store"


@dataclass(frozen=True)
class PieceInput:
    id: int
    name: str
    category: str
    unit_cost: float | None
    price: float | None
    units_made: int | None
    sales: tuple[SaleLine, ...] = ()


@dataclass(frozen=True)
class PieceResult:
    id: int
    name: str
    category: str
    unit_cost: float | None
    price: float | None
    units_made: int | None
    units_sold: int
    units_left: int | None
    sell_through: float | None
    revenue: float
    cost_of_sold: float | None
    gross_profit: float | None
    gross_margin: float | None
    avg_selling_price: float | None
    discount_rate: float | None
    stock_value_at_cost: float | None
    production_spend: float | None
    oversold: bool
    sold_by_size: dict[str, int]


@dataclass(frozen=True)
class DropResult:
    revenue: float
    units_sold: int
    units_made: int
    sell_through: float | None
    cost_of_sold: float
    gross_profit: float
    gross_margin: float | None
    expenses: float
    net_profit: float
    production_spend: float
    cash_back: float
    payback: float | None
    stock_value_at_cost: float
    break_even_units_left: int | None
    missing_costs: list[str] = field(default_factory=list)
    pieces: list[PieceResult] = field(default_factory=list)


def piece_result(p: PieceInput) -> PieceResult:
    sold = sum(s.quantity for s in p.sales)
    revenue = sum(s.quantity * s.unit_price for s in p.sales)
    by_size: dict[str, int] = defaultdict(int)
    for s in p.sales:
        if s.size:
            by_size[s.size] += s.quantity

    cost_of_sold = sold * p.unit_cost if p.unit_cost is not None else None
    gross = revenue - cost_of_sold if cost_of_sold is not None else None
    margin = (gross / revenue) if (gross is not None and revenue > 0) else None
    asp = revenue / sold if sold else None
    discount = (1 - asp / p.price) if (asp is not None and p.price) else None
    left = (p.units_made - sold) if p.units_made is not None else None
    st = (sold / p.units_made) if p.units_made else None
    stock_value = (max(left, 0) * p.unit_cost) if (left is not None and p.unit_cost is not None) else None
    spend = (p.units_made * p.unit_cost) if (p.units_made is not None and p.unit_cost is not None) else None

    return PieceResult(
        id=p.id,
        name=p.name,
        category=p.category,
        unit_cost=p.unit_cost,
        price=p.price,
        units_made=p.units_made,
        units_sold=sold,
        units_left=left,
        sell_through=round(st, 4) if st is not None else None,
        revenue=_r(revenue),
        cost_of_sold=_r(cost_of_sold) if cost_of_sold is not None else None,
        gross_profit=_r(gross) if gross is not None else None,
        gross_margin=round(margin, 4) if margin is not None else None,
        avg_selling_price=_r(asp) if asp is not None else None,
        discount_rate=round(max(discount, 0.0), 4) if discount is not None else None,
        stock_value_at_cost=_r(stock_value) if stock_value is not None else None,
        production_spend=_r(spend) if spend is not None else None,
        oversold=left is not None and left < 0,
        sold_by_size=dict(by_size),
    )


def drop_result(pieces: list[PieceInput], expenses: float = 0.0) -> DropResult:
    rows = [piece_result(p) for p in pieces]
    revenue = sum(r.revenue for r in rows)
    sold = sum(r.units_sold for r in rows)
    made = sum(r.units_made or 0 for r in rows)
    cos = sum(r.cost_of_sold or 0 for r in rows)
    gross = revenue - cos
    spend = sum(r.production_spend or 0 for r in rows)
    stock = sum(r.stock_value_at_cost or 0 for r in rows)
    missing = [r.name for r in rows if r.unit_cost is None]
    total_out = spend + expenses
    cash_back = revenue - total_out

    # How many more full-price units must sell to recover all money spent.
    break_even: int | None = None
    priced = [r for r in rows if r.price]
    if cash_back >= 0:
        break_even = 0
    elif priced:
        avg_price = sum(r.price for r in priced) / len(priced)  # type: ignore[misc]
        break_even = int(-(cash_back // avg_price))

    return DropResult(
        revenue=_r(revenue),
        units_sold=sold,
        units_made=made,
        sell_through=round(sold / made, 4) if made else None,
        cost_of_sold=_r(cos),
        gross_profit=_r(gross),
        gross_margin=round(gross / revenue, 4) if revenue else None,
        expenses=_r(expenses),
        net_profit=_r(gross - expenses),
        production_spend=_r(spend),
        cash_back=_r(cash_back),
        payback=round(revenue / total_out, 4) if total_out else None,
        stock_value_at_cost=_r(stock),
        break_even_units_left=break_even,
        missing_costs=missing,
        pieces=rows,
    )


def monthly_revenue(sales: list[SaleLine]) -> list[dict]:
    """Revenue and units per calendar month, oldest first, with empty months filled in."""
    if not sales:
        return []
    buckets: dict[str, list[float]] = defaultdict(lambda: [0.0, 0])
    for s in sales:
        key = s.sold_on.strftime("%Y-%m")
        buckets[key][0] += s.quantity * s.unit_price
        buckets[key][1] += s.quantity
    first, last = min(buckets), max(buckets)
    y, m = map(int, first.split("-"))
    out = []
    while True:
        key = f"{y:04d}-{m:02d}"
        rev, units = buckets.get(key, [0.0, 0])
        out.append({"month": key, "revenue": _r(rev), "units": int(units)})
        if key == last:
            break
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def channel_split(sales: list[SaleLine]) -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    for s in sales:
        out[s.channel] += s.quantity * s.unit_price
    return {k: _r(v) for k, v in out.items()}
