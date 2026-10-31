from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from ..db import get_db
from ..deps import get_ai
from ..schemas import ScoutIn, SignalIn, SignalOut, TrendReportOut
from ..services.ai import AIClient, TrendScout, scout_prompt
from ..services.context import brand_context, signals_text

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("/signals", response_model=list[SignalOut])
def list_signals(db: Session = Depends(get_db)):
    return db.scalars(select(m.TrendSignal).order_by(m.TrendSignal.created_at.desc())).all()


@router.post("/signals", response_model=SignalOut, status_code=201)
def add_signal(body: SignalIn, db: Session = Depends(get_db)):
    s = m.TrendSignal(**body.model_dump())
    db.add(s)
    db.commit()
    return s


@router.delete("/signals/{signal_id}", status_code=204)
def delete_signal(signal_id: int, db: Session = Depends(get_db)):
    s = db.get(m.TrendSignal, signal_id)
    if s is None:
        raise HTTPException(404, "That signal no longer exists.")
    db.delete(s)
    db.commit()


@router.post("/scout", response_model=TrendReportOut, status_code=201)
def scout(body: ScoutIn, db: Session = Depends(get_db), ai: AIClient = Depends(get_ai)):
    result = ai.structured(
        prompt=scout_prompt(brand_context(db), signals_text(db), body.launch_month, body.hint),
        schema=TrendScout,
        tool_name="trend_ranking",
    )
    report = m.TrendReport(launch_month=body.launch_month, hint=body.hint, result=result.model_dump())
    db.add(report)
    db.commit()
    return report


@router.get("/reports", response_model=list[TrendReportOut])
def list_reports(limit: int = 10, db: Session = Depends(get_db)):
    return db.scalars(select(m.TrendReport).order_by(m.TrendReport.created_at.desc()).limit(min(limit, 50))).all()
