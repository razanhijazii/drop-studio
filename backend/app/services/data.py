"""Bridges between database rows and the pure calculation services."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import models as m
from . import finance, planner


def f(x) -> float | None:
    return float(x) if x is not None else None


def get_profile(db: Session) -> m.BrandProfile:
    p = db.get(m.BrandProfile, 1)
    if p is None:
        p = m.BrandProfile(id=1)
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


def load_drop(db: Session, drop_id: int) -> m.Drop | None:
    return db.scalar(
        select(m.Drop)
        .where(m.Drop.id == drop_id)
        .options(
            selectinload(m.Drop.looks).selectinload(m.Look.pieces).selectinload(m.Piece.sales),
            selectinload(m.Drop.expenses),
        )
    )


def load_drops(db: Session, status: str | None = None) -> list[m.Drop]:
    q = (
        select(m.Drop)
        .options(
            selectinload(m.Drop.looks).selectinload(m.Look.pieces).selectinload(m.Piece.sales),
            selectinload(m.Drop.expenses),
        )
        .order_by(m.Drop.launched_on.desc().nulls_last(), m.Drop.created_at.desc())
    )
    if status:
        q = q.where(m.Drop.status == status)
    return list(db.scalars(q))


def piece_label(p: m.Piece) -> str:
    return p.name or f"{p.color} {p.category}".strip()


def sale_lines(p: m.Piece) -> tuple[finance.SaleLine, ...]:
    return tuple(
        finance.SaleLine(s.quantity, float(s.unit_price), s.sold_on, s.size, s.channel) for s in p.sales
    )


def piece_input(p: m.Piece) -> finance.PieceInput:
    return finance.PieceInput(
        id=p.id,
        name=piece_label(p),
        category=p.category,
        unit_cost=f(p.unit_cost),
        price=f(p.price),
        units_made=p.units_made,
        sales=sale_lines(p),
    )


def drop_pieces(d: m.Drop) -> list[m.Piece]:
    return [p for look in d.looks for p in look.pieces]


def drop_finance(d: m.Drop) -> finance.DropResult:
    expenses = sum(float(e.amount) for e in d.expenses)
    return finance.drop_result([piece_input(p) for p in drop_pieces(d)], expenses)


def history_for_planning(db: Session, exclude_id: int | None = None) -> list[planner.HistDrop]:
    """Launched drops with production numbers, newest first."""
    out = []
    for d in load_drops(db, status=None):
        if d.status not in ("launched", "closed") or d.id == exclude_id:
            continue
        pieces = []
        for p in drop_pieces(d):
            if not p.units_made:
                continue
            res = finance.piece_result(piece_input(p))
            pieces.append(planner.HistPiece(p.category, p.units_made, res.units_sold, res.sold_by_size))
        if pieces:
            out.append(planner.HistDrop(d.name, tuple(pieces)))
    return out


def category_history(db: Session, category: str) -> tuple[float | None, float | None]:
    """Recency-weighted sell-through and average discount for a category."""
    st_sum = disc_sum = w_sum = disc_w = 0.0
    for w, d in zip(planner.RECENCY_WEIGHTS, [d for d in load_drops(db) if d.status in ("launched", "closed")]):
        rows = [finance.piece_result(piece_input(p)) for p in drop_pieces(d) if p.category == category]
        made = sum(r.units_made or 0 for r in rows)
        if not made:
            continue
        sold = sum(min(r.units_sold, r.units_made or 0) for r in rows)
        st_sum += w * sold / made
        w_sum += w
        discs = [r.discount_rate for r in rows if r.discount_rate is not None]
        if discs:
            disc_sum += w * sum(discs) / len(discs)
            disc_w += w
    return (st_sum / w_sum if w_sum else None, disc_sum / disc_w if disc_w else None)
