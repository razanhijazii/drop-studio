from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..services.data import f, get_profile, history_for_planning, load_drop, piece_label
from ..services.planner import PlanSettings, plan_next_drop, split_sizes

router = APIRouter(prefix="/stock", tags=["stock"])


@router.get("/plan")
def plan(drop_id: int | None = None, db: Session = Depends(get_db)):
    """The production plan. With `drop_id`, also a per-piece plan and the cash it needs."""
    p = get_profile(db)
    settings = PlanSettings(baseline_units=p.first_drop_units, min_order_qty=p.min_order_qty)
    history = history_for_planning(db, exclude_id=drop_id)
    result = plan_next_drop(history, settings)
    out = {"currency": p.currency, "min_order_qty": p.min_order_qty, **asdict(result)}

    if drop_id is not None:
        d = load_drop(db, drop_id) or _404()
        by_cat = {c.category: c for c in result.categories}
        rows, cash, missing = [], 0.0, []
        for look in d.looks:
            for piece in look.pieces:
                cp = by_cat[piece.category]
                cost = f(piece.unit_cost)
                need = cost * cp.units_per_piece if cost is not None else None
                if need is None:
                    missing.append(piece_label(piece))
                else:
                    cash += need
                rows.append({
                    "piece_id": piece.id, "look": look.position, "name": piece_label(piece),
                    "category": piece.category, "units": cp.units_per_piece,
                    "by_size": split_sizes(cp.units_per_piece, result.size_curve),
                    "unit_cost": cost, "cash_needed": round(need, 2) if need is not None else None,
                    "current_units": piece.units_made, "below_moq": cp.below_moq,
                })
        out["drop"] = {"id": d.id, "name": d.name, "pieces": rows,
                       "total_units": sum(r["units"] for r in rows),
                       "cash_needed": round(cash, 2), "missing_costs": missing}
    return out


def _404():
    raise HTTPException(404, "That drop no longer exists.")
