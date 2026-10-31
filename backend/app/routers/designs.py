from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from .. import models as m
from ..config import Settings, get_settings
from ..db import get_db
from ..deps import get_ai
from ..services.ai import AIClient, DesignFeedback, review_prompt
from ..services.context import brand_context

router = APIRouter(prefix="/designs", tags=["designs"])

ALLOWED = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAGIC = {b"\x89PNG": "image/png", b"\xff\xd8\xff": "image/jpeg", b"GIF8": "image/gif"}


class DesignOut(BaseModel):
    id: int
    title: str
    drop_id: int | None
    note: str
    feedback: dict
    created_at: str
    image_url: str


def _out(r: m.DesignReview) -> DesignOut:
    return DesignOut(id=r.id, title=r.title, drop_id=r.drop_id, note=r.note, feedback=r.feedback,
                     created_at=r.created_at.isoformat(), image_url=f"/designs/{r.id}/image")


def _sniff(data: bytes) -> str | None:
    """Trust the bytes, not the filename or the browser's claimed type."""
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return next((t for sig, t in MAGIC.items() if data.startswith(sig)), None)


@router.post("/review", response_model=DesignOut, status_code=201)
async def review(
    image: UploadFile = File(...),
    title: str = Form("Untitled design"),
    note: str = Form(""),
    drop_id: int | None = Form(None),
    db: Session = Depends(get_db),
    ai: AIClient = Depends(get_ai),
    settings: Settings = Depends(get_settings),
):
    data = await image.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, f"Images must be under {settings.max_upload_bytes // (1024 * 1024)} MB.")
    kind = _sniff(data)
    if kind not in ALLOWED:
        raise HTTPException(415, "Upload a PNG, JPEG, WebP or GIF image.")

    drop_summary = ""
    if drop_id is not None:
        d = db.get(m.Drop, drop_id)
        if d is None:
            raise HTTPException(404, "That drop no longer exists.")
        drop_summary = f'This is for the drop "{d.name}" (trend: {d.trend}). Story: {d.story}'

    fb = await run_in_threadpool(
        ai.structured,
        prompt=review_prompt(brand_context(db), title, note, drop_summary),
        schema=DesignFeedback,
        tool_name="design_feedback",
        images=[(data, kind)],
    )
    r = m.DesignReview(title=title.strip() or "Untitled design", drop_id=drop_id, note=note, image=data,
                       image_type=kind, feedback=fb.model_dump())
    db.add(r)
    db.commit()
    return _out(r)


@router.get("", response_model=list[DesignOut])
def list_designs(drop_id: int | None = None, db: Session = Depends(get_db)):
    q = select(m.DesignReview).order_by(m.DesignReview.created_at.desc())
    if drop_id is not None:
        q = q.where(m.DesignReview.drop_id == drop_id)
    return [_out(r) for r in db.scalars(q)]


@router.get("/{design_id}/image")
def image(design_id: int, db: Session = Depends(get_db)):
    r = db.get(m.DesignReview, design_id)
    if r is None:
        raise HTTPException(404, "That design no longer exists.")
    return Response(r.image, media_type=r.image_type, headers={"Cache-Control": "private, max-age=86400"})


@router.delete("/{design_id}", status_code=204)
def delete_design(design_id: int, db: Session = Depends(get_db)):
    r = db.get(m.DesignReview, design_id)
    if r is None:
        raise HTTPException(404, "That design no longer exists.")
    db.delete(r)
    db.commit()
