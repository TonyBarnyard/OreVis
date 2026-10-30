import math

import pytest

from lending_agent import underwriting as uw


def test_monthly_payment_matches_known_value():
    # $1,000,000 at 7% over 25 years -> $7,067.79 (standard mortgage tables)
    assert uw.monthly_payment(1_000_000, 0.07, 25) == pytest.approx(7067.79, abs=0.01)


def test_zero_rate_payment_is_straight_line():
    assert uw.monthly_payment(120_000, 0.0, 10) == pytest.approx(1000.0)


def test_schedule_fully_amortizes():
    rows = uw.amortization_schedule(500_000, 0.065, 20)
    assert len(rows) == 240
    assert rows[-1]["balance"] == pytest.approx(0.0, abs=0.05)


def test_schedule_truncates_to_term_with_balloon():
    rows = uw.amortization_schedule(500_000, 0.065, 25, term_years=10)
    assert len(rows) == 120
    assert rows[-1]["balance"] > 0


def test_core_ratios():
    assert uw.dscr(150_000, 120_000) == pytest.approx(1.25)
    assert uw.ltv(750_000, 1_000_000) == pytest.approx(0.75)
    assert uw.debt_yield(90_000, 1_000_000) == pytest.approx(0.09)
    assert uw.breakeven_occupancy(40_000, 60_000, 125_000) == pytest.approx(0.8)
    assert uw.global_dscr(100_000, 50_000, 80_000, 20_000) == pytest.approx(1.5)


def test_interest_only_debt_service():
    assert uw.annual_debt_service(1_000_000, 0.08, 25, interest_only=True) == pytest.approx(80_000)


@pytest.mark.parametrize("fn,args", [
    (uw.dscr, (1, 0)), (uw.ltv, (1, 0)), (uw.debt_yield, (1, 0)),
    (uw.breakeven_occupancy, (1, 1, 0)), (uw.monthly_payment, (1, 0.05, 0)),
])
def test_bad_denominators_raise(fn, args):
    with pytest.raises(ValueError):
        fn(*args)


def test_size_loan_picks_binding_constraint_and_satisfies_all():
    r = uw.size_loan(noi=200_000, collateral_value=3_000_000, annual_rate=0.07,
                     amort_years=25, min_dscr=1.25, max_ltv=0.75, min_debt_yield=0.09)
    assert r.max_loan == min(r.max_loan_by_dscr, r.max_loan_by_ltv, r.max_loan_by_debt_yield)
    assert r.resulting_dscr >= 1.25 - 1e-9
    assert r.resulting_ltv <= 0.75 + 1e-9
    assert r.resulting_debt_yield >= 0.09 - 1e-9
    assert r.binding_constraint == "DSCR"


def test_size_loan_ltv_binds_on_low_value():
    r = uw.size_loan(noi=500_000, collateral_value=2_000_000, annual_rate=0.06, amort_years=25)
    assert r.binding_constraint == "LTV"
    assert r.max_loan == pytest.approx(1_500_000)


def test_rate_shock_lowers_dscr_monotonically():
    rows = uw.rate_shock(200_000, 2_000_000, 0.065, 25)
    dscrs = [row["dscr"] for row in rows]
    assert dscrs == sorted(dscrs, reverse=True)
    assert not math.isclose(dscrs[0], dscrs[-1])


def test_noi_sensitivity():
    rows = uw.noi_sensitivity(100_000, 1_000_000, 0.07, 25, noi_changes=(0.0, -0.1))
    assert rows[1]["dscr"] == pytest.approx(rows[0]["dscr"] * 0.9, rel=1e-3)
