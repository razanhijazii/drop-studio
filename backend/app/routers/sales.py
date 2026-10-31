from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .. import models as m
from ..db import get_db
from ..schemas import SaleIn, SaleOut
from ..services.data import piece_label

router = APIRouter(prefix="/sales", tags=["sales"])


def _out(s: m.Sale) -> SaleOut:
    look = s.piece.look
    return SaleOut.model_validate(s).model_copy(
        update={"piece_name": piece_label(s.piece), "drop_id": look.drop_id, "drop_name": look.drop.name}
    )


def _query():
    return select(m.Sale).options(joinedload(m.Sale.piece).joinedload(m.Piece.look).joinedload(m.Look.drop))


@router.get("", response_model=list[SaleOut])
def list_sales(drop_id: int | None = None, limit: int = 200, db: Session = Depends(get_db)):
    q = _query().order_by(m.Sale.sold_on.desc(), m.Sale.id.desc()).limit(min(limit, 2000))
    if drop_id is not None:
        q = q.join(m.Piece).join(m.Look).where(m.Look.drop_id == drop_id)
    return [_out(s) for s in db.scalars(q).unique()]


@router.post("", response_model=list[SaleOut], status_code=201)
def record_sales(body: SaleIn | list[SaleIn], db: Session = Depends(get_db)):
    """Log one sale or a batch (e.g. a day's till). Price defaults to the piece's list price."""
    items = body if isinstance(body, list) else [body]
    rows = []
    for item in items:
        piece = db.get(m.Piece, item.piece_id)
        if piece is None:
            raise HTTPException(404, f"Piece {item.piece_id} doesn't exist.")
        price = item.unit_price if item.unit_price is not None else piece.price
        if price is None:
            raise HTTPException(422, f"Set a price for {piece_label(piece)} first, or enter what it sold for.")
        rows.append(
            m.Sale(
                piece_id=piece.id,
                quantity=item.quantity,
                unit_price=price,
                size=item.size,
                sold_on=item.sold_on or date.today(),
                channel=item.channel,
                note=item.note,
            )
        )
    db.add_all(rows)
    db.commit()
    ids = [r.id for r in rows]
    return [_out(s) for s in db.scalars(_query().where(m.Sale.id.in_(ids)).order_by(m.Sale.id)).unique()]


@router.delete("/{sale_id}", status_code=204)
def delete_sale(sale_id: int, db: Session = Depends(get_db)):
    s = db.get(m.Sale, sale_id)
    if s is None:
        raise HTTPException(404, "That sale no longer exists.")
    db.delete(s)
    db.commit()
