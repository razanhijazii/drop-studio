"""The brand memory every AI prompt reads: profile, DNA rules, past drops, recent reviews."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from .data import drop_finance, get_profile, load_drops


def brand_context(db: Session) -> str:
    p = get_profile(db)
    parts = [f"BRAND: {p.name or '(unnamed)'}"]
    for label, value in (
        ("In one line", p.one_liner),
        ("Concepts and themes", p.concepts),
        ("Price feel", p.price_position),
        ("Customer", p.customer),
        ("Never do", p.never_do),
    ):
        if value:
            parts.append(f"{label}: {value}")

    rules = db.scalars(
        select(m.DnaRule).where(m.DnaRule.active.is_(True)).order_by(m.DnaRule.created_at.desc()).limit(50)
    ).all()
    if rules:
        parts.append("BRAND DNA RULES (follow these):\n" + "\n".join(f"- {r.text}" for r in rules))

    past = [d for d in load_drops(db) if d.status in ("launched", "closed")][:4]
    if past:
        lines = []
        for d in past:
            fin = drop_finance(d)
            st = f"{fin.sell_through:.0%}" if fin.sell_through is not None else "n/a"
            best = sorted(
                (r for r in fin.pieces if r.sell_through is not None), key=lambda r: r.sell_through, reverse=True
            )
            detail = ""
            if best:
                detail = f"; best seller {best[0].name} ({best[0].sell_through:.0%}), slowest {best[-1].name} ({best[-1].sell_through:.0%})"
            lines.append(f"- {d.name} (trend: {d.trend or 'n/a'}): sell-through {st}{detail}")
        parts.append("PAST DROPS:\n" + "\n".join(lines))

    reviews = db.scalars(select(m.DesignReview).order_by(m.DesignReview.created_at.desc()).limit(6)).all()
    if reviews:
        parts.append(
            "RECENT DESIGN REVIEWS:\n"
            + "\n".join(f"- {r.title}: {r.feedback.get('summary', '')}" for r in reviews if r.feedback)
        )
    return "\n\n".join(parts)


def signals_text(db: Session, limit: int = 40) -> str:
    sigs = db.scalars(select(m.TrendSignal).order_by(m.TrendSignal.created_at.desc()).limit(limit)).all()
    return "\n".join(
        f"- {s.title}{f' [{s.source}]' if s.source else ''}{': ' + s.note if s.note else ''}" for s in sigs
    )
