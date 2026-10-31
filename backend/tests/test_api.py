"""End-to-end flows through the HTTP API, with a fake AI."""

from __future__ import annotations

import io

from app.config import Settings


def test_health_and_config(client):
    assert client.get("/health").json() == {"ok": True}
    assert client.get("/config").json()["auth_required"] is False


def test_profile_roundtrip_and_validation(client):
    r = client.put("/brand/profile", json={"name": "Unplug", "currency": "usd", "target_margin": 0.7, "min_margin": 0.5})
    assert r.status_code == 200 and r.json()["currency"] == "USD"
    bad = client.put("/brand/profile", json={"min_margin": 0.8, "target_margin": 0.6})
    assert bad.status_code == 422


def test_dna_and_signals_crud(client):
    r = client.post("/brand/dna", json=[{"text": "Tonal logos only"}, {"text": "Heavy fleece"}])
    assert r.status_code == 201 and len(r.json()) == 2
    rid = r.json()[0]["id"]
    assert client.delete(f"/brand/dna/{rid}").status_code == 204
    assert len(client.get("/brand/dna").json()) == 1

    s = client.post("/trends/signals", json={"title": "Poll: 70% want brown", "source": "Instagram"})
    assert s.status_code == 201
    assert client.get("/trends/signals").json()[0]["title"].startswith("Poll")


def test_scout_uses_context_and_saves_report(client, fake_ai):
    client.post("/brand/dna", json={"text": "Never neon"})
    client.post("/trends/signals", json={"title": "Brown rising"})
    r = client.post("/trends/scout", json={"launch_month": "2027-01"})
    assert r.status_code == 201, r.text
    assert r.json()["result"]["trends"][0]["name"] == "Cocoa calm"
    prompt = fake_ai.calls[-1]["prompt"]
    assert "Never neon" in prompt and "Brown rising" in prompt and "2027-01" in prompt
    assert len(client.get("/trends/reports").json()) == 1
    assert client.post("/trends/scout", json={"launch_month": "2027-13"}).status_code == 422


def test_generate_then_save_drop(client):
    g = client.post("/drops/generate", json={"trend": "Cocoa calm", "launch_month": "2027-01"})
    assert g.status_code == 200, g.text
    draft = g.json()
    assert len(draft["looks"]) == 4
    saved = client.post("/drops", json=draft)
    assert saved.status_code == 201
    body = saved.json()
    assert len(body["looks"]) == 4 and len(body["looks"][0]["pieces"]) == 2
    assert client.get("/drops").json()[0]["name"] == "Offline"


def test_ai_not_configured_gives_clear_error(client):
    from app.deps import get_ai
    from app.services.ai import DisabledClient

    client.app.dependency_overrides[get_ai] = lambda: DisabledClient()
    r = client.post("/trends/scout", json={"launch_month": "2027-01"})
    assert r.status_code == 503 and "ANTHROPIC_API_KEY" in r.json()["detail"]


def test_look_limit_and_piece_edits(client, drop):
    r = client.post(f"/drops/{drop['id']}/looks", json={"name": "Fifth"})
    assert r.status_code == 409
    pid = drop["looks"][0]["pieces"][0]["id"]
    r = client.patch(f"/drops/pieces/{pid}", json={"price": 99.5, "made_by_size": {"S": 10, "M": 15}})
    assert r.status_code == 200
    assert r.json()["price"] == 99.5
    assert r.json()["units_made"] == 25  # size breakdown sets the total
    r = client.patch(f"/drops/pieces/{pid}", json={"made_by_size": {"S": 10, "M": 15}, "units_made": 40})
    assert r.json()["units_made"] == 40  # an explicit total wins


def test_sales_revenue_and_money_summary(client, drop):
    p1 = drop["looks"][0]["pieces"][0]  # hoodie 22 -> 95
    p2 = drop["looks"][0]["pieces"][1]  # pants 18 -> 85
    r = client.post("/sales", json=[
        {"piece_id": p1["id"], "quantity": 10, "size": "M", "sold_on": "2026-12-03"},
        {"piece_id": p1["id"], "quantity": 2, "unit_price": 80, "size": "L", "sold_on": "2026-12-20", "channel": "instagram"},
        {"piece_id": p2["id"], "quantity": 5, "sold_on": "2027-01-04"},
    ])
    assert r.status_code == 201, r.text
    assert r.json()[0]["unit_price"] == 95 and r.json()[0]["drop_name"] == "Drop One"
    client.post(f"/drops/{drop['id']}/expenses", json={"label": "Launch", "amount": 250})

    m = client.get(f"/money/drops/{drop['id']}").json()
    assert m["revenue"] == 10 * 95 + 2 * 80 + 5 * 85
    assert m["cost_of_sold"] == 12 * 22 + 5 * 18
    assert m["expenses"] == 250
    assert m["production_spend"] == 4 * 30 * (22 + 18)
    assert [x["month"] for x in m["by_month"]] == ["2026-12", "2027-01"]

    s = client.get("/money/summary").json()
    assert s["totals"]["revenue"] == m["revenue"]
    assert s["by_channel"]["instagram"] == 160
    assert s["drops"][0]["best_seller"] == "L1 hoodie"

    sale_id = r.json()[0]["id"]
    assert client.delete(f"/sales/{sale_id}").status_code == 204
    assert client.get("/money/summary").json()["totals"]["revenue"] == m["revenue"] - 950


def test_sale_needs_a_price(client, drop):
    look = drop["looks"][0]["id"]
    p = client.post(f"/drops/looks/{look}/pieces", json={"category": "t-shirt", "name": "Tee"}).json()
    r = client.post("/sales", json={"piece_id": p["id"], "quantity": 1})
    assert r.status_code == 422 and "price" in r.json()["detail"]


def test_pricing_uses_competitors_and_history(client, drop):
    for price in (90, 100, 110):
        client.post("/pricing/competitors", json={"brand": "X", "category": "hoodie", "price": price})
    first = client.post("/pricing/suggest", json={"unit_cost": 22, "category": "hoodie"}).json()
    assert first["market_median"] == 100 and first["recommended"] == 90

    # Sell every hoodie and launch the drop -> demand should push the hoodie price up.
    sales = [{"piece_id": lk["pieces"][0]["id"], "quantity": 30} for lk in drop["looks"]]
    client.post("/sales", json=sales)
    client.patch(f"/drops/{drop['id']}", json={"status": "launched"})
    after = client.post("/pricing/suggest", json={"unit_cost": 22, "category": "hoodie"}).json()
    assert after["recommended"] > first["recommended"]

    per_piece = client.get(f"/pricing/drops/{drop['id']}").json()
    assert len(per_piece) == 8 and "suggestion" in per_piece[0]


def test_stock_plan_first_then_learns(client, drop):
    client.put("/brand/profile", json={"first_drop_units": 25, "min_order_qty": 50})
    first = client.get("/stock/plan").json()
    assert first["first_drop"] and first["categories"][0]["units_per_piece"] == 25
    assert first["categories"][0]["below_moq"] is True

    sales = [{"piece_id": lk["pieces"][0]["id"], "quantity": 30, "size": "M"} for lk in drop["looks"]]
    sales += [{"piece_id": lk["pieces"][1]["id"], "quantity": 9, "size": "S"} for lk in drop["looks"]]
    client.post("/sales", json=sales)
    r = client.patch(f"/drops/{drop['id']}", json={"status": "launched"})
    assert r.json()["launched_on"] is not None

    plan = client.get("/stock/plan").json()
    cats = {c["category"]: c for c in plan["categories"]}
    assert not plan["first_drop"] and plan["based_on"] == ["Drop One"]
    assert cats["hoodie"]["units_per_piece"] > 30
    assert cats["sweatpants"]["units_per_piece"] < 30

    nxt = client.post("/drops", json={"name": "Drop Two", "looks": [{"position": 1, "pieces": [
        {"category": "hoodie", "unit_cost": 20}, {"category": "sweatpants"}]}]}).json()
    p = client.get(f"/stock/plan?drop_id={nxt['id']}").json()["drop"]
    assert p["total_units"] == cats["hoodie"]["units_per_piece"] + cats["sweatpants"]["units_per_piece"]
    assert p["cash_needed"] == cats["hoodie"]["units_per_piece"] * 20
    assert p["missing_costs"] == ["sweatpants"]


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def test_design_review_flow(client, fake_ai, drop):
    r = client.post(
        "/designs/review",
        data={"title": "Look 1 hoodie", "note": "boxy", "drop_id": str(drop["id"])},
        files={"image": ("sketch.png", io.BytesIO(PNG), "image/png")},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["feedback"]["scores"]["brand_fit"] == 8
    call = fake_ai.calls[-1]
    assert call["images"][0][1] == "image/png" and "Drop One" in call["prompt"]
    img = client.get(body["image_url"])
    assert img.status_code == 200 and img.content == PNG
    assert len(client.get("/designs").json()) == 1
    # The next review sees this one as brand memory.
    client.post("/designs/review", files={"image": ("b.png", io.BytesIO(PNG), "image/png")})
    assert "Strong base, shorten the hem." in fake_ai.calls[-1]["prompt"]


def test_design_review_rejects_non_images(client):
    r = client.post("/designs/review", files={"image": ("x.png", io.BytesIO(b"not an image"), "image/png")})
    assert r.status_code == 415


def test_delete_drop_cascades(client, drop):
    pid = drop["looks"][0]["pieces"][0]["id"]
    client.post("/sales", json={"piece_id": pid, "quantity": 1})
    assert client.delete(f"/drops/{drop['id']}").status_code == 204
    assert client.get("/sales").json() == []
    assert client.get(f"/drops/{drop['id']}").status_code == 404


def test_auth_required_when_password_set(engine, fake_ai):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from app.config import get_settings
    from app.db import get_db
    from app.deps import get_ai
    from app.main import create_app

    s = Settings(app_password="hunter2", secret_key="k" * 32)
    Session = sessionmaker(bind=engine)
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: s
    app.dependency_overrides[get_db] = lambda: (yield Session())
    app.dependency_overrides[get_ai] = lambda: fake_ai
    c = TestClient(app)
    assert c.get("/drops").status_code == 401
    assert c.post("/auth/login", json={"password": "wrong"}).status_code == 401
    tok = c.post("/auth/login", json={"password": "hunter2"}).json()["token"]
    assert c.get("/drops", headers={"Authorization": f"Bearer {tok}"}).status_code == 200
    assert c.get("/drops", headers={"Authorization": f"Bearer {tok}x"}).status_code == 401


def test_production_requires_password():
    import pytest

    with pytest.raises(RuntimeError):
        Settings(env="production").validate()
