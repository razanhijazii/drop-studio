from app.services.planner import HistDrop, HistPiece, PlanSettings, plan_next_drop, split_sizes


def by_cat(plan):
    return {c.category: c for c in plan.categories}


def test_first_drop_uses_baseline():
    p = plan_next_drop([], PlanSettings(baseline_units=30, min_order_qty=50))
    assert p.first_drop
    assert all(c.units_per_piece == 30 for c in p.categories)
    assert all(c.below_moq for c in p.categories)
    assert sum(by_cat(p)["hoodie"].by_size.values()) == 30


def test_sold_out_goes_up_slow_goes_down():
    hist = [HistDrop("D1", (
        HistPiece("hoodie", 30, 30), HistPiece("hoodie", 30, 29),
        HistPiece("t-shirt", 30, 9),
        HistPiece("sweatpants", 30, 22),
    ))]
    p = by_cat(plan_next_drop(hist))
    assert p["hoodie"].units_per_piece > 30
    assert "Sold out" in p["hoodie"].reason
    assert p["t-shirt"].units_per_piece < 30
    assert "Cut back" in p["t-shirt"].reason
    assert p["sweatpants"].units_per_piece == 25  # 22 * 1.1 = 24.2 -> 25
    assert p["sweatshirt"].units_per_piece == 30 and p["sweatshirt"].sell_through is None


def test_minimum_units_floor():
    p = by_cat(plan_next_drop([HistDrop("D1", (HistPiece("t-shirt", 30, 1),))]))
    assert p["t-shirt"].units_per_piece == 10


def test_recent_drop_counts_most():
    old = HistDrop("old", (HistPiece("hoodie", 30, 6),))
    new = HistDrop("new", (HistPiece("hoodie", 40, 40),))
    p = plan_next_drop([new, old])
    assert p.based_on == ["new", "old"]
    assert by_cat(p)["hoodie"].units_per_piece > 40


def test_size_curve_learns_from_sales():
    sizes = {"S": 10, "M": 100, "L": 40}
    p = plan_next_drop([HistDrop("D1", (HistPiece("hoodie", 150, 150, sizes),))])
    assert p.size_data_weight == 0.8
    assert p.size_curve["M"] > 0.5
    assert abs(sum(p.size_curve.values()) - 1) < 1e-3


def test_split_sizes_adds_up():
    for n in (1, 7, 30, 33, 101):
        assert sum(split_sizes(n, {"S": 0.33, "M": 0.34, "L": 0.33}).values()) == n
