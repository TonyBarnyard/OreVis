"""Tool schemas exposed to Claude, plus the dispatch table that runs them.

Each tool's description states *when* to call it (prescriptive triggering helps
recent Claude models reach for tools at the right moments). Handlers all take the
shared :class:`~finance_agent.store.Store` as the first argument.
"""

from __future__ import annotations

import json

from . import accounting, advising
from .store import Store


# --------------------------------------------------------------------------- #
# Client profile (lightweight key/value memory for advising context)
# --------------------------------------------------------------------------- #
def set_profile(store: Store, key: str, value: str) -> dict:
    with store.cursor() as cur:
        cur.execute(
            "INSERT INTO profile (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(key).strip(), str(value).strip()),
        )
    return {"saved": {key: value}}


def get_profile(store: Store, key: str | None = None) -> dict:
    if key:
        row = store.query_one("SELECT value FROM profile WHERE key = ?", (key,))
        return {"profile": {key: row["value"] if row else None}}
    rows = store.query("SELECT key, value FROM profile ORDER BY key")
    return {"profile": {r["key"]: r["value"] for r in rows}}


# --------------------------------------------------------------------------- #
# Dispatch table: tool name -> handler(store, **input)
# --------------------------------------------------------------------------- #
HANDLERS = {
    # Accounting
    "add_account": accounting.add_account,
    "seed_standard_chart": accounting.seed_standard_chart,
    "list_accounts": accounting.list_accounts,
    "record_journal_entry": accounting.record_journal_entry,
    "list_journal_entries": accounting.list_journal_entries,
    "general_ledger": accounting.general_ledger,
    "account_balance": accounting.account_balance,
    "trial_balance": accounting.trial_balance,
    "income_statement": accounting.income_statement,
    "balance_sheet": accounting.balance_sheet,
    "cash_flow_statement": accounting.cash_flow_statement,
    # Advising
    "loan_amortization": advising.loan_amortization,
    "investment_projection": advising.investment_projection,
    "savings_goal": advising.savings_goal,
    "retirement_projection": advising.retirement_projection,
    "budget_analysis": advising.budget_analysis,
    "net_worth": advising.net_worth,
    "tax_estimate": advising.tax_estimate,
    "financial_ratios": advising.financial_ratios,
    # Profile
    "set_profile": set_profile,
    "get_profile": get_profile,
}


def run_tool(store: Store, name: str, tool_input: dict) -> str:
    """Execute a tool and return a JSON string (always succeeds with a payload)."""
    handler = HANDLERS.get(name)
    if handler is None:
        return json.dumps({"error": f"Unknown tool '{name}'."})
    try:
        result = handler(store, **(tool_input or {}))
        return json.dumps(result, default=str)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except TypeError as e:
        return json.dumps({"error": f"Invalid arguments for {name}: {e}"})
    except Exception as e:  # last-resort guard so the loop never crashes
        return json.dumps({"error": f"{type(e).__name__}: {e}"})


# --------------------------------------------------------------------------- #
# Tool schemas (Anthropic Messages API format)
# --------------------------------------------------------------------------- #
def _obj(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required}


TOOLS = [
    # ----------------------------- Accounting ----------------------------- #
    {
        "name": "seed_standard_chart",
        "description": "Create a conventional small-business chart of accounts "
                       "(cash, A/R, A/P, revenue, common expenses, etc.). Call "
                       "this once when starting a fresh set of books and the user "
                       "has no accounts yet. Safe to call repeatedly; it skips "
                       "codes that already exist.",
        "input_schema": _obj({}, []),
    },
    {
        "name": "add_account",
        "description": "Add a single ledger account to the chart of accounts. Use "
                       "when the user needs an account that isn't already present.",
        "input_schema": _obj({
            "code": {"type": "string", "description": "Unique account number, e.g. '1000'."},
            "name": {"type": "string", "description": "Account name, e.g. 'Cash'."},
            "type": {"type": "string",
                     "enum": ["asset", "liability", "equity", "revenue", "expense"]},
        }, ["code", "name", "type"]),
    },
    {
        "name": "list_accounts",
        "description": "List all accounts in the chart of accounts with their type "
                       "and normal balance side. Call before posting entries if you "
                       "are unsure which account codes exist.",
        "input_schema": _obj({}, []),
    },
    {
        "name": "record_journal_entry",
        "description": "Post a balanced double-entry journal entry to the ledger. "
                       "Total debits must equal total credits. Use whenever the "
                       "user describes a transaction to record (a sale, a payment, "
                       "a purchase, payroll, etc.).",
        "input_schema": _obj({
            "date": {"type": "string", "description": "Entry date in YYYY-MM-DD."},
            "memo": {"type": "string", "description": "Short description of the transaction."},
            "lines": {
                "type": "array",
                "description": "Two or more lines. Each line debits OR credits one "
                               "account (not both).",
                "items": _obj({
                    "account_code": {"type": "string"},
                    "debit": {"type": "number", "description": "Debit amount (0 if a credit line)."},
                    "credit": {"type": "number", "description": "Credit amount (0 if a debit line)."},
                }, ["account_code"]),
            },
        }, ["date", "lines"]),
    },
    {
        "name": "list_journal_entries",
        "description": "List recent journal entries with their lines. Use to review "
                       "what has been recorded.",
        "input_schema": _obj({
            "limit": {"type": "integer", "description": "Max entries to return (default 50)."},
        }, []),
    },
    {
        "name": "general_ledger",
        "description": "Show every posting against one account with a running "
                       "balance. Use to audit or explain an account's activity.",
        "input_schema": _obj({
            "account_code": {"type": "string"},
        }, ["account_code"]),
    },
    {
        "name": "account_balance",
        "description": "Get the current balance of a single account.",
        "input_schema": _obj({
            "account_code": {"type": "string"},
        }, ["account_code"]),
    },
    {
        "name": "trial_balance",
        "description": "Produce a trial balance (all accounts with debit/credit "
                       "balances) and confirm the books are in balance. Use to "
                       "verify the ledger before producing statements.",
        "input_schema": _obj({
            "as_of": {"type": "string", "description": "Optional cutoff date YYYY-MM-DD."},
        }, []),
    },
    {
        "name": "income_statement",
        "description": "Generate a Profit & Loss statement (revenue minus expenses) "
                       "for a date range. Use when the user asks how the business "
                       "is performing or for a P&L.",
        "input_schema": _obj({
            "start": {"type": "string", "description": "Period start YYYY-MM-DD."},
            "end": {"type": "string", "description": "Period end YYYY-MM-DD."},
        }, ["start", "end"]),
    },
    {
        "name": "balance_sheet",
        "description": "Generate a balance sheet (assets, liabilities, equity) as of "
                       "a date, with current-period earnings folded into equity.",
        "input_schema": _obj({
            "as_of": {"type": "string", "description": "Optional date YYYY-MM-DD (default: all)."},
        }, []),
    },
    {
        "name": "cash_flow_statement",
        "description": "Show cash inflows/outflows and net change in the cash "
                       "account over a period (simplified direct method).",
        "input_schema": _obj({
            "start": {"type": "string"},
            "end": {"type": "string"},
            "cash_account_code": {"type": "string", "description": "Default '1000'."},
        }, ["start", "end"]),
    },
    # ----------------------------- Advising ------------------------------- #
    {
        "name": "loan_amortization",
        "description": "Amortize a fixed-rate loan or mortgage: monthly payment, "
                       "total interest, payoff time, and schedule. Supports extra "
                       "monthly payments. Use for any loan/mortgage question.",
        "input_schema": _obj({
            "principal": {"type": "number"},
            "annual_rate_pct": {"type": "number", "description": "Annual interest rate as a percent, e.g. 6.5."},
            "years": {"type": "number", "description": "Loan term in years."},
            "extra_monthly_payment": {"type": "number", "description": "Optional extra principal per month."},
        }, ["principal", "annual_rate_pct", "years"]),
    },
    {
        "name": "investment_projection",
        "description": "Project the future value of savings/investments with monthly "
                       "contributions, compounded monthly. Optionally adjusts for "
                       "inflation. Use for 'how much will I have' questions.",
        "input_schema": _obj({
            "present_value": {"type": "number"},
            "annual_return_pct": {"type": "number"},
            "years": {"type": "number"},
            "monthly_contribution": {"type": "number"},
            "annual_inflation_pct": {"type": "number", "description": "Optional, for real value."},
        }, ["present_value", "annual_return_pct", "years"]),
    },
    {
        "name": "savings_goal",
        "description": "Compute the monthly contribution needed to reach a target "
                       "amount by a target date. Use for 'how much should I save' "
                       "questions (down payment, college, emergency fund, etc.).",
        "input_schema": _obj({
            "target_amount": {"type": "number"},
            "years": {"type": "number"},
            "annual_return_pct": {"type": "number"},
            "present_value": {"type": "number", "description": "Amount already saved (default 0)."},
        }, ["target_amount", "years", "annual_return_pct"]),
    },
    {
        "name": "retirement_projection",
        "description": "Model retirement: accumulate savings to retirement age, then "
                       "draw down inflation-adjusted spending through life "
                       "expectancy. Reports the nest egg and whether it lasts.",
        "input_schema": _obj({
            "current_age": {"type": "integer"},
            "retirement_age": {"type": "integer"},
            "current_savings": {"type": "number"},
            "monthly_contribution": {"type": "number"},
            "annual_return_pct": {"type": "number"},
            "annual_spending_in_retirement": {"type": "number"},
            "life_expectancy": {"type": "integer", "description": "Default 90."},
            "annual_inflation_pct": {"type": "number", "description": "Default 2.5."},
        }, ["current_age", "retirement_age", "current_savings",
            "monthly_contribution", "annual_return_pct",
            "annual_spending_in_retirement"]),
    },
    {
        "name": "budget_analysis",
        "description": "Analyze a monthly budget against the 50/30/20 guideline and "
                       "report surplus/deficit. Use when the user shares income and "
                       "expenses or asks for budgeting help.",
        "input_schema": _obj({
            "monthly_after_tax_income": {"type": "number"},
            "expenses": {"type": "object", "description": "Map of category name to monthly amount.",
                         "additionalProperties": {"type": "number"}},
        }, ["monthly_after_tax_income", "expenses"]),
    },
    {
        "name": "net_worth",
        "description": "Compute net worth from assets and liabilities. Use for a net "
                       "worth statement or financial snapshot.",
        "input_schema": _obj({
            "assets": {"type": "object", "additionalProperties": {"type": "number"}},
            "liabilities": {"type": "object", "additionalProperties": {"type": "number"}},
        }, ["assets", "liabilities"]),
    },
    {
        "name": "tax_estimate",
        "description": "Estimate U.S. federal income tax (ordinary income, 2025 "
                       "brackets, standard or itemized deduction). Planning estimate "
                       "only — excludes FICA, state, credits. Use for tax-planning "
                       "and take-home-pay questions.",
        "input_schema": _obj({
            "gross_income": {"type": "number"},
            "filing_status": {"type": "string",
                              "enum": ["single", "married_joint", "head_of_household"]},
            "pre_tax_deductions": {"type": "number", "description": "e.g. 401(k), HSA contributions."},
            "itemized_deductions": {"type": "number", "description": "If itemizing instead of standard."},
        }, ["gross_income"]),
    },
    {
        "name": "financial_ratios",
        "description": "Compute liquidity, leverage, and profitability ratios from "
                       "balance-sheet and income-statement figures. Use for "
                       "financial analysis of a business.",
        "input_schema": _obj({
            "current_assets": {"type": "number"},
            "current_liabilities": {"type": "number"},
            "total_assets": {"type": "number"},
            "total_liabilities": {"type": "number"},
            "inventory": {"type": "number"},
            "cash_and_equivalents": {"type": "number"},
            "total_equity": {"type": "number"},
            "revenue": {"type": "number"},
            "gross_profit": {"type": "number"},
            "net_income": {"type": "number"},
            "ebit": {"type": "number"},
            "interest_expense": {"type": "number"},
        }, []),
    },
    # ----------------------------- Profile -------------------------------- #
    {
        "name": "set_profile",
        "description": "Save a fact about the client/business for later (e.g. "
                       "filing status, risk tolerance, fiscal year, goals). Use to "
                       "remember context the user states.",
        "input_schema": _obj({
            "key": {"type": "string"},
            "value": {"type": "string"},
        }, ["key", "value"]),
    },
    {
        "name": "get_profile",
        "description": "Retrieve saved client/business facts. Call at the start of "
                       "advising work to recall stored context.",
        "input_schema": _obj({
            "key": {"type": "string", "description": "Omit to return everything."},
        }, []),
    },
]
