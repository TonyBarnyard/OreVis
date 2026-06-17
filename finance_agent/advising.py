"""Financial-advising toolset: deterministic personal & corporate finance math.

Pure functions (no database) so the calculations are reproducible and auditable.
All currency outputs are rounded to cents and assume a single currency. Tax
figures are simplified U.S. federal estimates and are clearly labelled as such.
"""

from __future__ import annotations


def _round(x: float) -> float:
    return round(float(x), 2)


# --------------------------------------------------------------------------- #
# Loans & amortization
# --------------------------------------------------------------------------- #
def loan_amortization(principal: float, annual_rate_pct: float, years: float,
                      extra_monthly_payment: float = 0.0,
                      max_schedule_rows: int = 360) -> dict:
    """Amortize a fixed-rate loan with equal monthly payments.

    ``annual_rate_pct`` is a percentage (e.g. 6.5 for 6.5%). Returns the scheduled
    payment, total interest, payoff time, and a month-by-month schedule.
    """
    principal = float(principal)
    if principal <= 0:
        raise ValueError("principal must be positive.")
    n = int(round(years * 12))
    if n <= 0:
        raise ValueError("years must be positive.")
    r = (annual_rate_pct / 100.0) / 12.0
    extra = max(0.0, float(extra_monthly_payment))

    if r == 0:
        payment = principal / n
    else:
        payment = principal * r / (1 - (1 + r) ** -n)

    balance = principal
    total_interest = 0.0
    schedule = []
    month = 0
    while balance > 0.005 and month < 100000:
        month += 1
        interest = balance * r
        scheduled = payment + extra
        principal_paid = scheduled - interest
        if principal_paid >= balance:  # final (possibly partial) payment
            principal_paid = balance
            scheduled = balance + interest
        balance -= principal_paid
        total_interest += interest
        if len(schedule) < max_schedule_rows:
            schedule.append({
                "month": month,
                "payment": _round(scheduled),
                "interest": _round(interest),
                "principal": _round(principal_paid),
                "balance": _round(max(balance, 0.0)),
            })

    return {
        "principal": _round(principal),
        "annual_rate_pct": annual_rate_pct,
        "scheduled_monthly_payment": _round(payment),
        "extra_monthly_payment": _round(extra),
        "months_to_payoff": month,
        "years_to_payoff": _round(month / 12.0),
        "total_paid": _round(principal + total_interest),
        "total_interest": _round(total_interest),
        "schedule": schedule,
        "schedule_truncated": month > len(schedule),
    }


# --------------------------------------------------------------------------- #
# Investment growth & goals
# --------------------------------------------------------------------------- #
def investment_projection(present_value: float, annual_return_pct: float,
                          years: float, monthly_contribution: float = 0.0,
                          annual_inflation_pct: float = 0.0) -> dict:
    """Project the future value of savings with monthly contributions.

    Compounds monthly. If ``annual_inflation_pct`` is given, also reports the
    inflation-adjusted (today's-dollars) future value.
    """
    pv = float(present_value)
    n = int(round(years * 12))
    if n <= 0:
        raise ValueError("years must be positive.")
    r = (annual_return_pct / 100.0) / 12.0
    pmt = float(monthly_contribution)

    balance = pv
    contributed = pv
    yearly = []
    for month in range(1, n + 1):
        balance = balance * (1 + r) + pmt
        contributed += pmt
        if month % 12 == 0:
            yearly.append({"year": month // 12, "balance": _round(balance),
                           "contributed_to_date": _round(contributed)})

    fv = _round(balance)
    growth = _round(fv - contributed)
    result = {
        "present_value": _round(pv),
        "annual_return_pct": annual_return_pct,
        "years": years,
        "monthly_contribution": _round(pmt),
        "future_value": fv,
        "total_contributed": _round(contributed),
        "investment_growth": growth,
        "yearly": yearly,
    }
    if annual_inflation_pct:
        real = fv / ((1 + annual_inflation_pct / 100.0) ** years)
        result["annual_inflation_pct"] = annual_inflation_pct
        result["future_value_in_todays_dollars"] = _round(real)
    return result


def savings_goal(target_amount: float, years: float, annual_return_pct: float,
                 present_value: float = 0.0) -> dict:
    """Required monthly contribution to reach a savings target."""
    target = float(target_amount)
    n = int(round(years * 12))
    if n <= 0:
        raise ValueError("years must be positive.")
    r = (annual_return_pct / 100.0) / 12.0
    pv = float(present_value)

    fv_of_pv = pv * (1 + r) ** n
    remaining = target - fv_of_pv
    if remaining <= 0:
        monthly = 0.0
    elif r == 0:
        monthly = remaining / n
    else:
        monthly = remaining * r / ((1 + r) ** n - 1)

    return {
        "target_amount": _round(target),
        "years": years,
        "annual_return_pct": annual_return_pct,
        "starting_value": _round(pv),
        "required_monthly_contribution": _round(max(monthly, 0.0)),
        "projected_growth_on_starting_value": _round(fv_of_pv - pv),
        "already_on_track": remaining <= 0,
    }


def retirement_projection(current_age: int, retirement_age: int,
                          current_savings: float, monthly_contribution: float,
                          annual_return_pct: float,
                          annual_spending_in_retirement: float,
                          life_expectancy: int = 90,
                          annual_inflation_pct: float = 2.5) -> dict:
    """Model accumulation to retirement, then drawdown through life expectancy.

    Returns the projected nest egg at retirement and whether it is expected to
    last, with the age at which funds would run out if not.
    """
    if not (current_age < retirement_age < life_expectancy):
        raise ValueError(
            "Require current_age < retirement_age < life_expectancy."
        )
    r_month = (annual_return_pct / 100.0) / 12.0

    # Accumulation phase
    balance = float(current_savings)
    for _ in range((retirement_age - current_age) * 12):
        balance = balance * (1 + r_month) + monthly_contribution
    nest_egg = balance

    # Drawdown phase: spending grows with inflation; portfolio keeps earning.
    spend = float(annual_spending_in_retirement)
    r_year = annual_return_pct / 100.0
    infl = annual_inflation_pct / 100.0
    depleted_age = None
    trace = []
    for age in range(retirement_age, life_expectancy + 1):
        balance = balance * (1 + r_year) - spend
        trace.append({"age": age, "balance": _round(balance),
                      "annual_spending": _round(spend)})
        if balance < 0 and depleted_age is None:
            depleted_age = age
            break
        spend *= (1 + infl)

    lasts = depleted_age is None
    return {
        "nest_egg_at_retirement": _round(nest_egg),
        "retirement_age": retirement_age,
        "life_expectancy": life_expectancy,
        "first_year_spending": _round(annual_spending_in_retirement),
        "assumptions": {
            "annual_return_pct": annual_return_pct,
            "annual_inflation_pct": annual_inflation_pct,
            "monthly_contribution": _round(monthly_contribution),
        },
        "funds_last_through_life_expectancy": lasts,
        "funds_depleted_at_age": depleted_age,
        "drawdown_trace": trace,
    }


# --------------------------------------------------------------------------- #
# Budgeting & net worth
# --------------------------------------------------------------------------- #
def budget_analysis(monthly_after_tax_income: float, expenses: dict) -> dict:
    """Summarize a monthly budget and compare it to the 50/30/20 guideline.

    ``expenses`` maps category name -> monthly amount. Categories whose names
    suggest needs vs. wants are bucketed heuristically; unknown categories count
    as 'wants'. Anything left over is treated as savings.
    """
    income = float(monthly_after_tax_income)
    if income <= 0:
        raise ValueError("monthly_after_tax_income must be positive.")

    needs_kw = ("rent", "mortgage", "utility", "utilities", "grocery", "groceries",
                "insurance", "health", "medical", "transport", "transportation",
                "fuel", "gas", "childcare", "tuition", "loan", "debt", "minimum")
    total_expenses = 0.0
    needs = wants = 0.0
    breakdown = []
    for cat, amt in expenses.items():
        amt = float(amt)
        total_expenses += amt
        bucket = "needs" if any(k in cat.lower() for k in needs_kw) else "wants"
        if bucket == "needs":
            needs += amt
        else:
            wants += amt
        breakdown.append({"category": cat, "amount": _round(amt), "bucket": bucket})

    savings = income - total_expenses
    pct = lambda x: _round(100 * x / income)
    return {
        "monthly_income": _round(income),
        "total_expenses": _round(total_expenses),
        "monthly_surplus_or_deficit": _round(savings),
        "breakdown": breakdown,
        "actual": {"needs": _round(needs), "wants": _round(wants),
                   "savings": _round(max(savings, 0.0))},
        "actual_pct": {"needs": pct(needs), "wants": pct(wants),
                       "savings": pct(max(savings, 0.0))},
        "guideline_50_30_20": {
            "needs": _round(income * 0.50),
            "wants": _round(income * 0.30),
            "savings": _round(income * 0.20),
        },
        "note": "Needs/wants split is a heuristic from category names; adjust if "
                "a category is miscategorized.",
    }


def net_worth(assets: dict, liabilities: dict) -> dict:
    """Net worth = total assets - total liabilities."""
    total_assets = _round(sum(float(v) for v in assets.values()))
    total_liab = _round(sum(float(v) for v in liabilities.values()))
    return {
        "assets": {k: _round(float(v)) for k, v in assets.items()},
        "total_assets": total_assets,
        "liabilities": {k: _round(float(v)) for k, v in liabilities.items()},
        "total_liabilities": total_liab,
        "net_worth": _round(total_assets - total_liab),
    }


# --------------------------------------------------------------------------- #
# Tax estimate (U.S. federal, simplified)
# --------------------------------------------------------------------------- #
# 2025 federal ordinary-income brackets and standard deductions.
_BRACKETS_2025 = {
    "single": [(0, 0.10), (11925, 0.12), (48475, 0.22), (103350, 0.24),
               (197300, 0.32), (250525, 0.35), (626350, 0.37)],
    "married_joint": [(0, 0.10), (23850, 0.12), (96950, 0.22), (206700, 0.24),
                      (394600, 0.32), (501050, 0.35), (751600, 0.37)],
    "head_of_household": [(0, 0.10), (17000, 0.12), (64850, 0.22), (103350, 0.24),
                          (197300, 0.32), (250500, 0.35), (626350, 0.37)],
}
_STD_DEDUCTION_2025 = {
    "single": 15000, "married_joint": 30000, "head_of_household": 22500,
}

# 2025 long-term capital-gains breakpoints (taxable income). Below ``zero_top``
# the rate is 0%; up to ``fifteen_top`` it is 15%; above it is 20%.
_LTCG_BREAKS_2025 = {
    "single": {"zero_top": 48350, "fifteen_top": 533400},
    "married_joint": {"zero_top": 96700, "fifteen_top": 600050},
    "married_separate": {"zero_top": 48350, "fifteen_top": 300000},
    "head_of_household": {"zero_top": 64750, "fifteen_top": 566700},
}

# Net Investment Income Tax: a flat 3.8% surtax. Thresholds are statutory (not
# inflation-indexed) and apply to modified AGI (MAGI).
_NIIT_RATE = 0.038
_NIIT_THRESHOLDS = {
    "single": 200000, "head_of_household": 200000,
    "married_joint": 250000, "married_separate": 125000,
}


def _normalize_status(filing_status: str) -> str:
    status = filing_status.lower().strip().replace(" ", "_")
    aliases = {
        "married": "married_joint", "mfj": "married_joint", "joint": "married_joint",
        "mfs": "married_separate", "married_filing_separately": "married_separate",
        "separate": "married_separate", "hoh": "head_of_household",
    }
    status = aliases.get(status, status)
    if status not in _BRACKETS_2025 and status not in _LTCG_BREAKS_2025:
        raise ValueError(
            f"filing_status must be one of {sorted(_LTCG_BREAKS_2025)} "
            f"(got '{filing_status}')."
        )
    return status


def _ordinary_tax(taxable: float, status: str) -> tuple[float, float]:
    """Return (tax, marginal_rate) on ordinary taxable income for a filing status.

    ``married_separate`` falls back to single brackets (a close approximation for
    a planning estimate)."""
    brackets = _BRACKETS_2025.get(status) or _BRACKETS_2025["single"]
    taxable = max(0.0, taxable)
    tax = 0.0
    marginal_rate = brackets[0][1]
    for i, (floor, rate) in enumerate(brackets):
        ceiling = brackets[i + 1][0] if i + 1 < len(brackets) else float("inf")
        if taxable > floor:
            tax += (min(taxable, ceiling) - floor) * rate
            marginal_rate = rate
        else:
            break
    return tax, marginal_rate


def tax_estimate(gross_income: float, filing_status: str = "single",
                 pre_tax_deductions: float = 0.0,
                 itemized_deductions: float | None = None,
                 tax_year: int = 2025) -> dict:
    """Estimate U.S. federal income tax (ordinary income only).

    Uses 2025 brackets and the standard deduction unless ``itemized_deductions``
    is larger. Excludes FICA, state/local tax, credits, AMT, and capital gains —
    this is a planning estimate, not tax advice or a filed return.
    """
    status = _normalize_status(filing_status)

    gross = float(gross_income)
    agi = max(0.0, gross - float(pre_tax_deductions))
    std = _STD_DEDUCTION_2025.get(status, _STD_DEDUCTION_2025["single"])
    deduction = max(std, float(itemized_deductions)) if itemized_deductions else std
    taxable = max(0.0, agi - deduction)

    tax, marginal_rate = _ordinary_tax(taxable, status)

    return {
        "tax_year": tax_year,
        "filing_status": status,
        "gross_income": _round(gross),
        "pre_tax_deductions": _round(float(pre_tax_deductions)),
        "agi": _round(agi),
        "deduction_used": _round(deduction),
        "deduction_type": "itemized" if (itemized_deductions and itemized_deductions > std)
                          else "standard",
        "taxable_income": _round(taxable),
        "estimated_federal_tax": _round(tax),
        "marginal_rate_pct": _round(marginal_rate * 100),
        "effective_rate_pct": _round(100 * tax / gross) if gross else 0.0,
        "after_tax_income": _round(gross - tax),
        "disclaimer": "Simplified U.S. federal estimate for planning only. Excludes "
                      "FICA, state/local taxes, credits, AMT, and capital gains. "
                      "Not tax advice.",
    }


# --------------------------------------------------------------------------- #
# Capital gains tax (U.S. federal, simplified)
# --------------------------------------------------------------------------- #
def capital_gains_tax(filing_status: str = "single",
                      long_term_gain: float = 0.0,
                      short_term_gain: float = 0.0,
                      other_taxable_income: float = 0.0,
                      magi: float | None = None,
                      state_rate_pct: float = 0.0,
                      tax_year: int = 2025) -> dict:
    """Estimate U.S. federal tax on capital gains.

    Models the real mechanics:
      * Short-term gains (assets held <= 1 year) are taxed as ORDINARY income —
        their tax is the *incremental* ordinary tax they add on top of
        ``other_taxable_income`` (your taxable income excluding these gains).
      * Long-term gains (held > 1 year) get preferential 0%/15%/20% rates and are
        "stacked" on top of ordinary income (including short-term gains) to find
        which brackets they fill.
      * The 3.8% Net Investment Income Tax (NIIT) applies to the lesser of net
        investment income or the amount of MAGI above the statutory threshold.
      * An optional flat ``state_rate_pct`` is applied to total gains for a rough
        all-in figure.

    Planning estimate only — excludes AMT, collectibles (28%) and unrecaptured
    §1250 (25%) special rates, loss limits, and state nuances. Not tax advice.
    """
    status = _normalize_status(filing_status)
    lt = max(0.0, float(long_term_gain))
    st = max(0.0, float(short_term_gain))
    ordinary = max(0.0, float(other_taxable_income))

    # --- Short-term gains: incremental ordinary tax -----------------------
    base_tax, _ = _ordinary_tax(ordinary, status)
    with_st_tax, st_marginal = _ordinary_tax(ordinary + st, status)
    short_term_tax = with_st_tax - base_tax

    # --- Long-term gains: stack on top of ordinary income + short-term -----
    breaks = _LTCG_BREAKS_2025[status]
    z, f = breaks["zero_top"], breaks["fifteen_top"]
    stack_base = ordinary + st          # LTCG sits above all ordinary income
    band_top = stack_base + lt
    amt_0 = max(0.0, min(band_top, z) - stack_base)
    amt_15 = max(0.0, min(band_top, f) - max(stack_base, z))
    amt_20 = max(0.0, band_top - max(stack_base, f))
    long_term_tax = amt_15 * 0.15 + amt_20 * 0.20

    # --- Net Investment Income Tax (3.8%) ---------------------------------
    nii = lt + st
    magi_val = (ordinary + st + lt) if magi is None else float(magi)
    threshold = _NIIT_THRESHOLDS[status]
    niit = _NIIT_RATE * min(nii, max(0.0, magi_val - threshold))

    # --- Optional flat state tax ------------------------------------------
    state_tax = (state_rate_pct / 100.0) * (lt + st)

    federal_total = long_term_tax + short_term_tax + niit
    total = federal_total + state_tax
    blended = _round(100 * total / (lt + st)) if (lt + st) else 0.0

    return {
        "tax_year": tax_year,
        "filing_status": status,
        "long_term_gain": _round(lt),
        "short_term_gain": _round(st),
        "other_taxable_income": _round(ordinary),
        "long_term_breakdown": {
            "taxed_at_0pct": _round(amt_0),
            "taxed_at_15pct": _round(amt_15),
            "taxed_at_20pct": _round(amt_20),
            "long_term_tax": _round(long_term_tax),
        },
        "short_term_tax": _round(short_term_tax),
        "short_term_marginal_rate_pct": _round(st_marginal * 100),
        "niit_3_8pct": _round(niit),
        "magi_used": _round(magi_val),
        "state_tax": _round(state_tax),
        "total_federal_tax_on_gains": _round(federal_total),
        "total_tax_on_gains": _round(total),
        "net_after_tax_proceeds": _round((lt + st) - total),
        "blended_rate_on_gains_pct": blended,
        "disclaimer": "Simplified U.S. federal estimate for planning only. "
                      "Excludes AMT, collectibles/§1250 special rates, capital-loss "
                      "limits, and most state rules. Not tax advice. See the "
                      "tax_strategies tool for ways to reduce these gains.",
    }


# --------------------------------------------------------------------------- #
# Financial ratios
# --------------------------------------------------------------------------- #
def financial_ratios(current_assets: float = 0, current_liabilities: float = 0,
                     total_assets: float = 0, total_liabilities: float = 0,
                     inventory: float = 0, cash_and_equivalents: float = 0,
                     total_equity: float = 0, revenue: float = 0,
                     gross_profit: float = 0, net_income: float = 0,
                     ebit: float = 0, interest_expense: float = 0) -> dict:
    """Compute common liquidity, leverage, and profitability ratios.

    Pass whatever figures you have; ratios needing a missing/zero denominator are
    returned as null.
    """
    def div(a, b):
        return _round(a / b) if b else None

    return {
        "liquidity": {
            "current_ratio": div(current_assets, current_liabilities),
            "quick_ratio": div(current_assets - inventory, current_liabilities),
            "cash_ratio": div(cash_and_equivalents, current_liabilities),
        },
        "leverage": {
            "debt_to_equity": div(total_liabilities, total_equity),
            "debt_to_assets": div(total_liabilities, total_assets),
            "equity_multiplier": div(total_assets, total_equity),
            "interest_coverage": div(ebit, interest_expense),
        },
        "profitability": {
            "gross_margin_pct": div(100 * gross_profit, revenue),
            "net_margin_pct": div(100 * net_income, revenue),
            "return_on_assets_pct": div(100 * net_income, total_assets),
            "return_on_equity_pct": div(100 * net_income, total_equity),
        },
    }
