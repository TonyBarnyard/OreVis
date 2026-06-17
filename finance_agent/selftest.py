"""Offline self-test for the deterministic tools (no API key needed).

Run with:  python -m finance_agent.selftest
Exercises the ledger and the financial math, asserting known-good results.
"""

from __future__ import annotations

import math
import os
import tempfile

import json

from . import accounting as A
from . import advising as F
from . import knowledge as K
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


def test_capital_gains():
    # $20k long-term gain stacked above $50k ordinary income (single) -> all 15%.
    cg = F.capital_gains_tax("single", long_term_gain=20000, other_taxable_income=50000)
    _approx(cg["long_term_breakdown"]["long_term_tax"], 3000)
    _approx(cg["total_tax_on_gains"], 3000)
    assert cg["niit_3_8pct"] == 0

    # 0%-bracket harvesting: $10k LT gain, only $30k other income -> $0 tax.
    cg0 = F.capital_gains_tax("single", long_term_gain=10000, other_taxable_income=30000)
    _approx(cg0["total_tax_on_gains"], 0)
    _approx(cg0["long_term_breakdown"]["taxed_at_0pct"], 10000)

    # NIIT kicks in: $50k LT gain over $190k ordinary income (single).
    # LTCG: 50000*15% = 7500. NIIT: 3.8% * min(50000, 240000-200000=40000) = 1520.
    cgn = F.capital_gains_tax("single", long_term_gain=50000, other_taxable_income=190000)
    _approx(cgn["long_term_breakdown"]["long_term_tax"], 7500)
    _approx(cgn["niit_3_8pct"], 1520)
    _approx(cgn["total_tax_on_gains"], 9020)

    # Short-term gain is taxed as ordinary income (incremental).
    cgs = F.capital_gains_tax("single", short_term_gain=10000, other_taxable_income=60000)
    assert cgs["short_term_tax"] > 0
    assert cgs["long_term_breakdown"]["long_term_tax"] == 0

    print("✓ capital gains: LT stacking, 0%-bracket, NIIT, short-term ordinary")


def test_knowledge_and_dispatch():
    from .store import Store
    from .tools import HANDLERS, TOOLS, run_tool

    # Knowledge bank returns facts + indexed strategies, and is queryable.
    idx = K.tax_strategies()
    assert idx["facts"]["tax_year"] == 2025
    assert any(s["id"] == "tax_loss_harvesting" for s in idx["strategy_index"])
    one = K.tax_strategies(strategy_id="primary_residence_121")
    assert "121" in one["strategy"]["irc"]
    hits = K.tax_strategies(query="real estate")
    assert hits["match_count"] >= 1

    # Tool registry is consistent and dispatch routes store vs pure tools.
    names = {t["name"] for t in TOOLS}
    assert names == set(HANDLERS), names ^ set(HANDLERS)

    store = Store(os.path.join(tempfile.mkdtemp(), "dispatch.db"))
    # Pure tool through the dispatcher (must NOT receive the store).
    out = json.loads(run_tool(store, "capital_gains_tax",
                              {"filing_status": "single", "long_term_gain": 20000,
                               "other_taxable_income": 50000}))
    _approx(out["total_tax_on_gains"], 3000)
    # Store-backed tool through the dispatcher.
    A2 = json.loads(run_tool(store, "seed_standard_chart", {}))
    assert "added_codes" in A2
    # Knowledge tool through the dispatcher.
    strat = json.loads(run_tool(store, "tax_strategies", {"query": "charity"}))
    assert strat["match_count"] >= 1
    store.close()

    print("✓ knowledge bank + tool dispatch (store vs pure routing)")


def main() -> int:
    test_ledger()
    test_advising()
    test_capital_gains()
    test_knowledge_and_dispatch()
    print("\nAll self-tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
