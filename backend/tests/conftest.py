from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import db as db_module
from app.config import Settings, get_settings
from app.db import Base, get_db, make_engine
from app.deps import get_ai
from app.main import create_app
from app.services import ai as ai_mod


class FakeAI:
    """Returns canned, schema-valid answers and records what it was asked."""

    def __init__(self):
        self.calls: list[dict] = []

    def structured(self, *, prompt, schema, tool_name, images=None):
        self.calls.append({"prompt": prompt, "tool": tool_name, "images": images})
        colours = [{"name": "Cocoa", "hex": "#5B3A2C"}, {"name": "Cloud", "hex": "#ECEAE4"},
                   {"name": "Teal", "hex": "#1F6F6B"}]
        if schema is ai_mod.TrendScout:
            idea = {"name": "Cocoa calm", "fit": 88, "lifespan": "season", "why": "Brown is rising.",
                    "our_take": "Heavy cocoa fleece.", "colours": colours[:2],
                    "search_terms": ["cocoa fleece", "brown hoodie", "quiet luxury lounge"], "avoid": "Logo mania"}
            return schema.model_validate({"trends": [idea] * 3, "summary": "Go cocoa."})
        if schema is ai_mod.DropConcept:
            look = {"name": "Look", "signature_detail": "Tonal stitch",
                    "pieces": [
                        {"category": "hoodie", "name": "Hood", "color": "Cocoa", "fit": "Boxy", "fabric": "Fleece", "gsm": 420},
                        {"category": "sweatpants", "name": "Pant", "color": "Cocoa", "fit": "Relaxed", "fabric": "Fleece", "gsm": 400},
                    ]}
            return schema.model_validate({
                "name": "Offline", "story": "Unplug.", "palette": colours, "looks": [look] * 4,
                "store": {"lighting": "Warm", "scent": "Cedar", "sound": "Quiet", "display": "Tables", "ritual": "Tea"},
                "moodboard": ["a", "b", "c", "d"], "avoid": ["neon"],
            })
        if schema is ai_mod.DesignFeedback:
            return schema.model_validate({
                "summary": "Strong base, shorten the hem.",
                "scores": {"brand_fit": 8, "trend": 7, "effortless": 8, "wearability": 9},
                "works": ["Colour"], "change": ["Drop the shoulder 2 cm"], "dna_takeaways": ["Hems stay clean"],
            })
        raise AssertionError(f"unexpected schema {schema}")


@pytest.fixture
def engine():
    eng = make_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def fake_ai():
    return FakeAI()


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def client(engine, fake_ai, settings, monkeypatch):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(db_module, "SessionLocal", Session)
    import app.main as main_mod
    monkeypatch.setattr(main_mod, "SessionLocal", Session)

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app = create_app()
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_ai] = lambda: fake_ai
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as c:
        yield c


@pytest.fixture
def drop(client):
    """A saved drop with 4 looks x 2 pieces, costs and prices set."""
    looks = []
    specs = [("hoodie", 22, 95), ("sweatpants", 18, 85)]
    for i in range(1, 5):
        looks.append({"position": i, "name": f"Look {i}", "pieces": [
            {"category": c, "name": f"L{i} {c}", "unit_cost": cost, "price": price, "units_made": 30}
            for c, cost, price in specs
        ]})
    r = client.post("/drops", json={"name": "Drop One", "trend": "Cocoa", "launch_month": "2026-12", "looks": looks})
    assert r.status_code == 201, r.text
    return r.json()
