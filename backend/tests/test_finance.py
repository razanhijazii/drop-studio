from datetime import date

import pytest

from app.services.finance import PieceInput, SaleLine, channel_split, drop_result, monthly_revenue, piece_result

D = date(2026, 11, 5)


def piece(**kw):
    base = dict(id=1, name="Hoodie", category="hoodie", unit_cost=20.0, price=100.0, units_made=30, sales=())
    base.update(kw)
    return PieceInput(**base)


def test_piece_with_no_sales():
    r = piece_result(piece())
    assert r.units_sold == 0 and r.revenue == 0
    assert r.sell_through == 0
    assert r.units_left == 30
    assert r.stock_value_at_cost == 600
    assert r.gross_margin is None and r.avg_selling_price is None


def test_piece_full_price_and_discounted_sales():
    sales = (SaleLine(10, 100.0, D, "M"), SaleLine(5, 80.0, D, "L"))
    r = piece_result(piece(sales=sales))
    assert r.units_sold == 15
    assert r.revenue == 1400
    assert r.cost_of_sold == 300
    assert r.gross_profit == 1100
    assert r.gross_margin == pytest.approx(1100 / 1400, abs=1e-4)
    assert r.avg_selling_price == pytest.approx(93.33, abs=0.01)
    assert r.discount_rate == pytest.approx(0.0667, abs=1e-3)
    assert r.sell_through == 0.5
    assert r.sold_by_size == {"M": 10, "L": 5}


def test_missing_cost_does_not_crash_and_is_reported():
    r = drop_result([piece(unit_cost=None, sales=(SaleLine(2, 100.0, D),))])
    assert r.revenue == 200
    assert r.missing_costs == ["Hoodie"]
    assert r.pieces[0].gross_profit is None


def test_oversold_is_flagged():
    r = piece_result(piece(units_made=2, sales=(SaleLine(3, 100.0, D),)))
    assert r.oversold and r.units_left == -1
    assert r.stock_value_at_cost == 0


def test_drop_profit_versus_cash():
    # 2 pieces x 30 made at 20 = 1200 spent, plus 300 expenses.
    a = piece(id=1, sales=(SaleLine(20, 100.0, D),))
    b = piece(id=2, name="Pant", sales=(SaleLine(5, 100.0, D),))
    r = drop_result([a, b], expenses=300)
    assert r.revenue == 2500
    assert r.cost_of_sold == 500
    assert r.gross_profit == 2000
    assert r.net_profit == 1700
    assert r.production_spend == 1200
    assert r.cash_back == 1000
    assert r.break_even_units_left == 0
    assert r.stock_value_at_cost == 700
    assert r.sell_through == pytest.approx(25 / 60, abs=1e-4)


def test_break_even_units_when_still_in_the_red():
    r = drop_result([piece(sales=(SaleLine(3, 100.0, D),))], expenses=0)
    # spent 600, earned 300 -> 300 short at 100 each = 3 more sales
    assert r.cash_back == -300
    assert r.break_even_units_left == 3


def test_monthly_revenue_fills_gaps():
    s = [SaleLine(1, 50.0, date(2026, 11, 3)), SaleLine(2, 50.0, date(2027, 1, 9))]
    assert monthly_revenue(s) == [
        {"month": "2026-11", "revenue": 50.0, "units": 1},
        {"month": "2026-12", "revenue": 0.0, "units": 0},
        {"month": "2027-01", "revenue": 100.0, "units": 2},
    ]
    assert monthly_revenue([]) == []


def test_channel_split():
    s = [SaleLine(1, 50.0, D, channel="store"), SaleLine(2, 40.0, D, channel="instagram")]
    assert channel_split(s) == {"store": 50.0, "instagram": 80.0}
