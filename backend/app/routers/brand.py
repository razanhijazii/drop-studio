from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from ..db import get_db
from ..schemas import DnaIn, DnaOut, ProfileIn, ProfileOut
from ..services.data import get_profile

router = APIRouter(prefix="/brand", tags=["brand"])


@router.get("/profile", response_model=ProfileOut)
def read_profile(db: Session = Depends(get_db)):
    return get_profile(db)


@router.put("/profile", response_model=ProfileOut)
def save_profile(body: ProfileIn, db: Session = Depends(get_db)):
    if body.min_margin > body.target_margin:
        raise HTTPException(422, "Minimum margin can't be higher than the target margin.")
    p = get_profile(db)
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@router.get("/dna", response_model=list[DnaOut])
def list_dna(db: Session = Depends(get_db)):
    return db.scalars(select(m.DnaRule).order_by(m.DnaRule.created_at.desc())).all()


@router.post("/dna", response_model=list[DnaOut], status_code=201)
def add_dna(body: DnaIn | list[DnaIn], db: Session = Depends(get_db)):
    items = body if isinstance(body, list) else [body]
    rows = [m.DnaRule(**i.model_dump()) for i in items]
    db.add_all(rows)
    db.commit()
    return rows


@router.patch("/dna/{rule_id}", response_model=DnaOut)
def update_dna(rule_id: int, body: DnaIn, db: Session = Depends(get_db)):
    r = db.get(m.DnaRule, rule_id) or _404()
    for k, v in body.model_dump().items():
        setattr(r, k, v)
    db.commit()
    return r


@router.delete("/dna/{rule_id}", status_code=204)
def delete_dna(rule_id: int, db: Session = Depends(get_db)):
    db.delete(db.get(m.DnaRule, rule_id) or _404())
    db.commit()


def _404():
    raise HTTPException(404, "That rule no longer exists.")
