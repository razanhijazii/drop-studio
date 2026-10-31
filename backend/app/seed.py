"""Load starter data.

    python -m app.seed            brand concepts, DNA rules and this season's trend signals
    python -m app.seed --demo     also a sample launched drop with sales, clearly named as a demo

Safe to run twice: it skips anything that already exists.
"""

from __future__ import annotations

import argparse
import random
from datetime import date, timedelta

from sqlalchemy import select

from . import models as m
from .db import SessionLocal
from .services.data import get_profile

SIGNALS = [
    ("Pantone 2026 Colour of the Year: Cloud Dancer, a soft grayish white", "Pantone",
     "Chosen as a response to overstimulation and a wish for less toxicity and excess. Matches the unplugging concept.",
     "https://www.dezeen.com/?p=2275626"),
    ("WGSN x Coloro AW26/27 key colours", "WGSN",
     "Transformative Teal (colour of the year), Wax Paper off-white as the new neutral, Fresh Purple, Cocoa Powder brown, Green Glow.",
     "https://fashionunited.uk/news/fashion/spotted-on-the-catwalk-wgsn-and-coloros-colour-trends-for-aw26-27/2024091377535"),
    ("FW26 colours rising: deep brown +50%, purple +60%, burgundy +46% YoY", "Trendalytics",
     "Search growth year on year. Electric teal rising as an accent among key influencers.",
     "https://trendalytics.co/insights/fall-winter-2026-fashion-trends-colors-prints-fabrics"),
    ("FW26 aesthetics: elevated luxury on neutral bases, heritage preppy, early-2010s nostalgia", "Trendalytics",
     "Soft fabrics paired with heavy textures. Tartan +40% YoY, argyle +24% among influencers.",
     "https://trendalytics.co/insights/fall-winter-2026-fashion-trends-colors-prints-fabrics"),
]

DNA = [
    "Only 4 complete outfits per drop, each one a look people come in already wanting.",
    "Luxury comes from fabric weight, fit and one quiet signature detail, never from big logos.",
]

def seed(demo: bool = False) -> None:
    with SessionLocal() as db:
        p = get_profile(db)
        if not p.concepts:
            p.one_liner = "Premium everyday basics with a community feel: upscale, never Gucci-level luxury."
            p.concepts = "Pursuing your dreams. Unplugging from technology and toxic surroundings."
            p.price_position = "Above high street, well below luxury"
            p.never_do = "Trying too hard. Loud logos."
        if not db.scalar(select(m.DnaRule.id).limit(1)):
            db.add_all(m.DnaRule(text=t, source="founder's concept") for t in DNA)
        if not db.scalar(select(m.TrendSignal.id).limit(1)):
            db.add_all(m.TrendSignal(title=t, source=s, note=n, url=u) for t, s, n, u in SIGNALS)
        if demo and not db.scalar(select(m.Drop.id).where(m.Drop.name.like("DEMO%"))):
            _demo(db)
        db.commit()


def _demo(db) -> None:
    rnd = random.Random(7)
    launch = date.today() - timedelta(days=60)
    d = m.Drop(name="DEMO: Offline", trend="Cocoa and cloud neutrals", launch_month=launch.strftime("%Y-%m"),
               story="Sample data to try the money and stock pages. Delete it when your first real drop launches.",
               status="launched", launched_on=launch)
    specs = [
        ("hoodie", "Cocoa hoodie", 22, 95, 30, 30), ("sweatpants", "Cocoa sweatpants", 18, 85, 30, 24),
        ("t-shirt", "Cloud tee", 8, 45, 30, 17), ("sweatpants", "Cloud sweatpants", 18, 85, 30, 21),
        ("sweatshirt", "Teal crew", 20, 90, 30, 12), ("sweatpants", "Teal sweatpants", 18, 85, 30, 10),
        ("hoodie", "Wax zip hoodie", 25, 110, 30, 28), ("t-shirt", "Wax tee", 8, 45, 30, 22),
    ]
    for i in range(4):
        look = m.Look(position=i + 1, name=f"Look {i + 1}")
        for cat, name, cost, price, made, sold in specs[i * 2:i * 2 + 2]:
            piece = m.Piece(category=cat, name=name, unit_cost=cost, price=price, units_made=made)
            for _ in range(sold):
                piece.sales.append(m.Sale(
                    quantity=1, unit_price=price, size=rnd.choices(["S", "M", "L", "XL"], [2, 4, 3, 1])[0],
                    sold_on=launch + timedelta(days=rnd.randint(0, 55)),
                    channel=rnd.choice(["store", "store", "store", "instagram"]),
                ))
            look.pieces.append(piece)
        d.looks.append(look)
    d.expenses = [m.Expense(label="Launch night", amount=300), m.Expense(label="Packaging", amount=120)]
    db.add(d)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    seed(ap.parse_args().demo)
    print("Seeded.")
