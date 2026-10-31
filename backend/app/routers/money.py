"""Revenue, profit and pricing."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from ..db import get_db
from ..schemas import CompetitorIn, CompetitorOut, PriceQuery
from ..services import finance
from ..services.data import (
    category_history,
    drop_finance,
    drop_pieces,
    f,
    get_profile,
    load_drop,
    load_drops,
    piece_label,
    sale_lines,
)
from ..services.pricing import PricingInput, suggest_price

router = APIRouter(tags=["money"])


@router.get("/money/summary")
def summary(db: Session = Depends(get_db)):
    """Brand-wide totals, per-drop results, and revenue by month."""
    profile = get_profile(db)
    drops = load_drops(db)
    per_drop = []
    all_sales: list[finance.SaleLine] = []
    totals = dict(revenue=0.0, gross_profit=0.0, net_profit=0.0, expenses=0.0, production_spend=0.0,
                  cash_back=0.0, stock_value_at_cost=0.0, units_sold=0)
    for d in drops:
        fin = drop_finance(d)
        for p in drop_pieces(d):
            all_sales.extend(sale_lines(p))
        for k in totals:
            totals[k] += getattr(fin, k)
        best = max((r for r in fin.pieces if r.units_sold), key=lambda r: r.revenue, default=None)
        per_drop.append({
            "id": d.id, "name": d.name, "status": d.status, "launch_month": d.launch_month,
            **{k: getattr(fin, k) for k in (
                "revenue", "units_sold", "units_made", "sell_through", "gross_profit", "gross_margin",
                "expenses", "net_profit", "production_spend", "cash_back", "payback", "stock_value_at_cost",
                "break_even_units_left",
            )},
            "missing_costs": fin.missing_costs,
            "best_seller": best.name if best else None,
        })
    totals = {k: round(v, 2) if isinstance(v, float) else v for k, v in totals.items()}
    totals["gross_margin"] = round(totals["gross_profit"] / totals["revenue"], 4) if totals["revenue"] else None
    return {
        "currency": profile.currency,
        "totals": totals,
        "drops": per_drop,
        "by_month": finance.monthly_revenue(all_sales),
        "by_channel": finance.channel_split(all_sales),
    }


@router.get("/money/drops/{drop_id}")
def drop_money(drop_id: int, db: Session = Depends(get_db)):
    d = load_drop(db, drop_id)
    if d is None:
        raise HTTPException(404, "That drop no longer exists.")
    fin = drop_finance(d)
    sales = [s for p in drop_pieces(d) for s in sale_lines(p)]
    return {"currency": get_profile(db).currency, **asdict(fin), "by_month": finance.monthly_revenue(sales)}


# ------------------------------------------------------------- pricing

@router.get("/pricing/competitors", response_model=list[CompetitorOut])
def list_competitors(db: Session = Depends(get_db)):
    return db.scalars(select(m.CompetitorPrice).order_by(m.CompetitorPrice.category, m.CompetitorPrice.price)).all()


@router.post("/pricing/competitors", response_model=CompetitorOut, status_code=201)
def add_competitor(body: CompetitorIn, db: Session = Depends(get_db)):
    c = m.CompetitorPrice(**body.model_dump())
    db.add(c)
    db.commit()
    return c


@router.delete("/pricing/competitors/{cid}", status_code=204)
def delete_competitor(cid: int, db: Session = Depends(get_db)):
    c = db.get(m.CompetitorPrice, cid)
    if c is None:
        raise HTTPException(404, "That price no longer exists.")
    db.delete(c)
    db.commit()


def _suggest(db: Session, unit_cost: float, category: str, current: float | None) -> dict:
    p = get_profile(db)
    comps = db.scalars(select(m.CompetitorPrice.price).where(m.CompetitorPrice.category == category)).all()
    st, disc = category_history(db, category)
    try:
        res = suggest_price(PricingInput(
            unit_cost=unit_cost, category=category,
            target_margin=float(p.target_margin), min_margin=float(p.min_margin),
            market_position=float(p.market_position),
            competitor_prices=tuple(float(c) for c in comps),
            past_sell_through=st, past_discount_rate=disc, current_price=current,
        ))
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return {"currency": p.currency, **asdict(res)}


@router.post("/pricing/suggest")
def suggest(body: PriceQuery, db: Session = Depends(get_db)):
    return _suggest(db, body.unit_cost, body.category, body.current_price)


@router.get("/pricing/drops/{drop_id}")
def suggest_for_drop(drop_id: int, db: Session = Depends(get_db)):
    """A suggestion for every piece in a drop that has a unit cost."""
    d = load_drop(db, drop_id)
    if d is None:
        raise HTTPException(404, "That drop no longer exists.")
    out = []
    for look in d.looks:
        for piece in look.pieces:
            row = {"piece_id": piece.id, "look": look.position, "name": piece_label(piece),
                   "category": piece.category, "unit_cost": f(piece.unit_cost), "price": f(piece.price)}
            if piece.unit_cost and piece.unit_cost > 0:
                row["suggestion"] = _suggest(db, float(piece.unit_cost), piece.category, f(piece.price))
            out.append(row)
    return out
