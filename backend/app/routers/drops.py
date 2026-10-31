from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models as m
from ..db import get_db
from ..deps import get_ai
from ..schemas import (
    DropIn,
    DropOut,
    DropSummary,
    DropUpdate,
    ExpenseIn,
    ExpenseOut,
    GenerateDropIn,
    LookIn,
    LookOut,
    LookUpdate,
    PieceIn,
    PieceOut,
    PieceUpdate,
)
from ..services.ai import AIClient, DropConcept, drop_prompt
from ..services.context import brand_context
from ..services.data import drop_finance, load_drop, load_drops

router = APIRouter(prefix="/drops", tags=["drops"])


def _drop(db: Session, drop_id: int) -> m.Drop:
    d = load_drop(db, drop_id)
    if d is None:
        raise HTTPException(404, "That drop no longer exists.")
    return d


def _build_looks(looks: list[LookIn]) -> list[m.Look]:
    out = []
    for i, look in enumerate(looks, start=1):
        out.append(
            m.Look(
                position=look.position if look.position else i,
                name=look.name,
                signature_detail=look.signature_detail,
                pieces=[m.Piece(**p.model_dump()) for p in look.pieces],
            )
        )
    return out


@router.get("", response_model=list[DropSummary])
def list_drops(db: Session = Depends(get_db)):
    out = []
    for d in load_drops(db):
        fin = drop_finance(d)
        out.append(
            DropSummary.model_validate(d).model_copy(
                update={
                    "revenue": fin.revenue,
                    "units_sold": fin.units_sold,
                    "sell_through": fin.sell_through,
                    "net_profit": fin.net_profit,
                }
            )
        )
    return out


@router.post("", response_model=DropOut, status_code=201)
def create_drop(body: DropIn, db: Session = Depends(get_db)):
    data = body.model_dump(exclude={"looks"})
    d = m.Drop(**data, looks=_build_looks(body.looks))
    db.add(d)
    db.commit()
    return _drop(db, d.id)


@router.post("/generate", response_model=DropIn)
def generate_drop(body: GenerateDropIn, db: Session = Depends(get_db), ai: AIClient = Depends(get_ai)):
    """Draft four looks with Claude. Nothing is saved until you POST the result to /drops."""
    c = ai.structured(
        prompt=drop_prompt(brand_context(db), body.trend, body.launch_month, body.direction),
        schema=DropConcept,
        tool_name="drop_concept",
    )
    return DropIn(
        name=c.name,
        trend=body.trend,
        launch_month=body.launch_month,
        story=c.story,
        palette=[p.model_dump() for p in c.palette],
        store=c.store.model_dump(),
        moodboard=c.moodboard,
        avoid=c.avoid,
        looks=[
            LookIn(
                position=i,
                name=look.name,
                signature_detail=look.signature_detail,
                pieces=[PieceIn(**p.model_dump()) for p in look.pieces],
            )
            for i, look in enumerate(c.looks, start=1)
        ],
    )


@router.get("/{drop_id}", response_model=DropOut)
def read_drop(drop_id: int, db: Session = Depends(get_db)):
    return _drop(db, drop_id)


@router.patch("/{drop_id}", response_model=DropOut)
def update_drop(drop_id: int, body: DropUpdate, db: Session = Depends(get_db)):
    d = _drop(db, drop_id)
    changes = body.model_dump(exclude_unset=True)
    if changes.get("status") == "launched" and d.launched_on is None and "launched_on" not in changes:
        changes["launched_on"] = date.today()
    for k, v in changes.items():
        setattr(d, k, v)
    db.commit()
    return _drop(db, drop_id)


@router.delete("/{drop_id}", status_code=204)
def delete_drop(drop_id: int, db: Session = Depends(get_db)):
    db.delete(_drop(db, drop_id))
    db.commit()


# ---- looks

@router.post("/{drop_id}/looks", response_model=LookOut, status_code=201)
def add_look(drop_id: int, body: LookIn, db: Session = Depends(get_db)):
    d = _drop(db, drop_id)
    if len(d.looks) >= 4:
        raise HTTPException(409, "A drop has four looks. Remove one before adding another.")
    taken = {lk.position for lk in d.looks}
    body.position = next(p for p in range(1, 5) if p not in taken) if body.position in taken else body.position
    look = _build_looks([body])[0]
    d.looks.append(look)
    db.commit()
    return look


@router.patch("/looks/{look_id}", response_model=LookOut)
def update_look(look_id: int, body: LookUpdate, db: Session = Depends(get_db)):
    look = db.get(m.Look, look_id) or _missing("look")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(look, k, v)
    db.commit()
    return look


@router.delete("/looks/{look_id}", status_code=204)
def delete_look(look_id: int, db: Session = Depends(get_db)):
    db.delete(db.get(m.Look, look_id) or _missing("look"))
    db.commit()


# ---- pieces

@router.post("/looks/{look_id}/pieces", response_model=PieceOut, status_code=201)
def add_piece(look_id: int, body: PieceIn, db: Session = Depends(get_db)):
    look = db.get(m.Look, look_id) or _missing("look")
    piece = m.Piece(**body.model_dump())
    look.pieces.append(piece)
    db.commit()
    return piece


@router.patch("/pieces/{piece_id}", response_model=PieceOut)
def update_piece(piece_id: int, body: PieceUpdate, db: Session = Depends(get_db)):
    piece = db.get(m.Piece, piece_id) or _missing("piece")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(piece, k, v)
    # A size breakdown defines the total unless a total was sent explicitly.
    if body.made_by_size and "units_made" not in body.model_fields_set:
        piece.units_made = sum(body.made_by_size.values())
    db.commit()
    db.refresh(piece)
    return piece


@router.delete("/pieces/{piece_id}", status_code=204)
def delete_piece(piece_id: int, db: Session = Depends(get_db)):
    db.delete(db.get(m.Piece, piece_id) or _missing("piece"))
    db.commit()


# ---- expenses

@router.post("/{drop_id}/expenses", response_model=ExpenseOut, status_code=201)
def add_expense(drop_id: int, body: ExpenseIn, db: Session = Depends(get_db)):
    d = _drop(db, drop_id)
    e = m.Expense(**body.model_dump())
    d.expenses.append(e)
    db.commit()
    return e


@router.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    db.delete(db.get(m.Expense, expense_id) or _missing("expense"))
    db.commit()


def _missing(what: str):
    raise HTTPException(404, f"That {what} no longer exists.")
