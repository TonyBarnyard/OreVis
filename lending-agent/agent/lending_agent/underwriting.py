"""Deterministic commercial-lending math used by the agent's tools.

The model never does arithmetic "in its head" for credit metrics: every number
that lands in a credit memo or spreadsheet comes from these functions, so the
output is reproducible and auditable by the subscriber who makes the decision.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict


def monthly_payment(principal: float, annual_rate: float, amort_years: float) -> float:
    """Level monthly payment for a fully amortizing loan."""
    n = round(amort_years * 12)
    if n <= 0:
        raise ValueError("amortization must be positive")
    r = annual_rate / 12
    if r == 0:
        return principal / n
    return principal * r / (1 - (1 + r) ** -n)


def annual_debt_service(principal: float, annual_rate: float, amort_years: float,
                        interest_only: bool = False) -> float:
    if interest_only:
        return principal * annual_rate
    return monthly_payment(principal, annual_rate, amort_years) * 12


def amortization_schedule(principal: float, annual_rate: float, amort_years: float,
                          term_years: float | None = None) -> list[dict]:
    """Month-by-month schedule through the term (or full amortization)."""
    pmt = monthly_payment(principal, annual_rate, amort_years)
    months = round((term_years or amort_years) * 12)
    balance = principal
    rows = []
    for m in range(1, months + 1):
        interest = balance * annual_rate / 12
        principal_paid = min(pmt - interest, balance)
        balance -= principal_paid
        rows.append({
            "month": m,
            "payment": round(pmt, 2),
            "interest": round(interest, 2),
            "principal": round(principal_paid, 2),
            "balance": round(max(balance, 0.0), 2),
        })
    return rows


def dscr(noi: float, debt_service: float) -> float:
    if debt_service <= 0:
        raise ValueError("debt service must be positive")
    return noi / debt_service


def ltv(loan_amount: float, collateral_value: float) -> float:
    if collateral_value <= 0:
        raise ValueError("collateral value must be positive")
    return loan_amount / collateral_value


def debt_yield(noi: float, loan_amount: float) -> float:
    if loan_amount <= 0:
        raise ValueError("loan amount must be positive")
    return noi / loan_amount


def breakeven_occupancy(operating_expenses: float, debt_service: float,
                        gross_potential_income: float) -> float:
    if gross_potential_income <= 0:
        raise ValueError("gross potential income must be positive")
    return (operating_expenses + debt_service) / gross_potential_income


def global_dscr(business_cash_flow: float, personal_cash_flow: float,
                business_debt_service: float, personal_debt_service: float) -> float:
    """Combined borrower + guarantor coverage (common for SBA / owner-occupied CRE)."""
    return dscr(business_cash_flow + personal_cash_flow,
                business_debt_service + personal_debt_service)


@dataclass
class SizingResult:
    max_loan_by_dscr: float
    max_loan_by_ltv: float
    max_loan_by_debt_yield: float
    max_loan: float
    binding_constraint: str
    annual_debt_service: float
    resulting_dscr: float
    resulting_ltv: float
    resulting_debt_yield: float

    def to_dict(self) -> dict:
        return {k: round(v, 4) if isinstance(v, float) else v for k, v in asdict(self).items()}


def size_loan(noi: float, collateral_value: float, annual_rate: float, amort_years: float,
              min_dscr: float = 1.25, max_ltv: float = 0.75,
              min_debt_yield: float = 0.09) -> SizingResult:
    """Maximum loan that satisfies all three policy constraints at once."""
    constant = annual_debt_service(1.0, annual_rate, amort_years)  # debt service per $1 of loan
    by_dscr = noi / min_dscr / constant
    by_ltv = collateral_value * max_ltv
    by_dy = noi / min_debt_yield if min_debt_yield > 0 else float("inf")
    candidates = {"DSCR": by_dscr, "LTV": by_ltv, "Debt yield": by_dy}
    binding = min(candidates, key=candidates.get)
    loan = candidates[binding]
    ds = loan * constant
    return SizingResult(by_dscr, by_ltv, by_dy, loan, binding, ds,
                        dscr(noi, ds), ltv(loan, collateral_value), debt_yield(noi, loan))


def rate_shock(noi: float, loan_amount: float, annual_rate: float, amort_years: float,
               shocks_bps: tuple[int, ...] = (0, 100, 200, 300)) -> list[dict]:
    """DSCR under rate increases -- standard stress test for floating or refi risk."""
    out = []
    for bps in shocks_bps:
        rate = annual_rate + bps / 10_000
        ds = annual_debt_service(loan_amount, rate, amort_years)
        out.append({"shock_bps": bps, "rate": round(rate, 4),
                    "annual_debt_service": round(ds, 2), "dscr": round(noi / ds, 3)})
    return out


def noi_sensitivity(noi: float, loan_amount: float, annual_rate: float, amort_years: float,
                    noi_changes: tuple[float, ...] = (0.0, -0.05, -0.10, -0.20)) -> list[dict]:
    ds = annual_debt_service(loan_amount, annual_rate, amort_years)
    return [{"noi_change": c, "noi": round(noi * (1 + c), 2), "dscr": round(noi * (1 + c) / ds, 3)}
            for c in noi_changes]
