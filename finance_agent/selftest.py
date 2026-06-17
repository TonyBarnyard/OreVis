"""Offline self-test for the deterministic tools (no API key needed).

Run with:  python -m finance_agent.selftest
Exercises the ledger and the financial math, asserting known-good results.
"""

from __future__ import annotations

import math
import os
import tempfile

from . import accounting as A
from . import advising as F
from .store import Store


def _approx(a, b, tol=0.02):
    assert abs(a - b) <= tol, f"expected ~{b}, got {a}"


def test_ledger():
    path = os.path.join(tempfile.mkdtemp(), "test_ledger.db")
    store = Store(path)
    A.seed_standard_chart(store)

    # Owner invests $10,000 cash.
    A.record_journal_entry(store, "2026-01-01", [
        {"account_code": "1000", "debit": 10000},
        {"account_code": "3000", "credit": 10000},
    ], memo="Initial capital")

    # Invoice a client $4,000 for services (on account).
    A.record_journal_entry(store, "2026-01-15", [
        {"account_code": "1100", "debit": 4000},
        {"account_code": "4100", "credit": 4000},
    ], memo="Consulting invoice")

    # Pay $1,200 rent in cash.
    A.record_journal_entry(store, "2026-01-31", [
        {"account_code": "6000", "debit": 1200},
        {"account_code": "1000", "credit": 1200},
    ], memo="January rent")

    tb = A.trial_balance(store)
    assert tb["in_balance"], "trial balance must tie"
    _approx(tb["total_debit"], tb["total_credit"])

    pnl = A.income_statement(store, "2026-01-01", "2026-01-31")
    _approx(pnl["total_revenue"], 4000)
    _approx(pnl["total_expenses"], 1200)
    _approx(pnl["net_income"], 2800)

    bs = A.balance_sheet(store, "2026-01-31")
    assert bs["balances"], "balance sheet must balance"
    _approx(bs["total_assets"], 12800)  # 8800 cash + 4000 A/R

    cash = A.account_balance(store, "1000")
    _approx(cash["balance"], 8800)

    # Unbalanced entry must be rejected.
    try:
        A.record_journal_entry(store, "2026-02-01", [
            {"account_code": "1000", "debit": 100},
            {"account_code": "4000", "credit": 90},
        ])
        raise AssertionError("unbalanced entry should have raised")
    except ValueError:
        pass

    store.close()
    print("✓ ledger: chart, entries, trial balance, P&L, balance sheet")


def test_advising():
    # 30-yr $200k mortgage at 6% -> payment ~ $1199.10.
    loan = F.loan_amortization(200000, 6.0, 30)
    _approx(loan["scheduled_monthly_payment"], 1199.10, tol=0.10)
    assert loan["months_to_payoff"] == 360

    # $0 start, 7%/yr, 10 yrs, $100/mo -> FV ~ $17,308.
    proj = F.investment_projection(0, 7.0, 10, 100)
    _approx(proj["future_value"], 17308.48, tol=1.0)

    # Save for $50k in 5 yrs at 5%, starting at 0 -> ~ $735.27/mo.
    goal = F.savings_goal(50000, 5, 5.0, 0)
    _approx(goal["required_monthly_contribution"], 735.27, tol=0.5)

    # Tax: single, $120k gross, $10k pre-tax -> taxable 95k.
    # 10%*11925 + 12%*36550 + 22%*46525 = 15814.00
    tax = F.tax_estimate(120000, "single", pre_tax_deductions=10000)
    _approx(tax["taxable_income"], 95000)
    _approx(tax["estimated_federal_tax"], 15814.0, tol=1.0)
    assert tax["marginal_rate_pct"] == 22.0

    nw = F.net_worth({"home": 400000, "401k": 150000}, {"mortgage": 250000})
    _approx(nw["net_worth"], 300000)

    ratios = F.financial_ratios(current_assets=200, current_liabilities=100,
                                total_liabilities=300, total_equity=150)
    _approx(ratios["liquidity"]["current_ratio"], 2.0)
    _approx(ratios["leverage"]["debt_to_equity"], 2.0)

    budget = F.budget_analysis(7500, {"Rent": 2200, "Groceries": 600,
                                      "Dining": 500, "Subscriptions": 120})
    _approx(budget["monthly_surplus_or_deficit"], 4080)

    ret = F.retirement_projection(35, 65, 80000, 1500, 6.5, 60000)
    assert ret["nest_egg_at_retirement"] > 0
    assert math.isfinite(ret["nest_egg_at_retirement"])

    print("✓ advising: loans, projections, goals, tax, net worth, ratios, budget")


def main() -> int:
    test_ledger()
    test_advising()
    print("\nAll self-tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
