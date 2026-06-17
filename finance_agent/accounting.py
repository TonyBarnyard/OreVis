"""Accounting toolset: a persistent double-entry bookkeeping ledger.

Each function takes a :class:`~finance_agent.store.Store` and returns a plain,
JSON-serializable dict (or raises ``ValueError`` with a message the agent can
relay). All monetary amounts are rounded to cents.
"""

from __future__ import annotations

from .store import ACCOUNT_TYPES, Store

# Amounts are compared with a half-cent tolerance to absorb float rounding.
_TOL = 0.005


def _round(x: float) -> float:
    return round(float(x), 2)


def _account_by_code(store: Store, code: str):
    row = store.query_one("SELECT * FROM accounts WHERE code = ?", (code,))
    if row is None:
        raise ValueError(
            f"No account with code '{code}'. Use list_accounts or add_account first."
        )
    return row


# --------------------------------------------------------------------------- #
# Chart of accounts
# --------------------------------------------------------------------------- #
def add_account(store: Store, code: str, name: str, type: str) -> dict:
    """Create a new ledger account."""
    type = type.lower().strip()
    if type not in ACCOUNT_TYPES:
        raise ValueError(
            f"type must be one of {sorted(ACCOUNT_TYPES)} (got '{type}')."
        )
    code = str(code).strip()
    existing = store.query_one("SELECT id FROM accounts WHERE code = ?", (code,))
    if existing:
        raise ValueError(f"Account code '{code}' already exists.")
    with store.cursor() as cur:
        cur.execute(
            "INSERT INTO accounts (code, name, type) VALUES (?, ?, ?)",
            (code, name.strip(), type),
        )
    return {
        "created": {"code": code, "name": name.strip(), "type": type,
                    "normal_balance": ACCOUNT_TYPES[type]}
    }


def seed_standard_chart(store: Store) -> dict:
    """Populate a small, conventional small-business chart of accounts.

    Skips any code that already exists, so it is safe to call more than once.
    """
    standard = [
        ("1000", "Cash", "asset"),
        ("1100", "Accounts Receivable", "asset"),
        ("1200", "Inventory", "asset"),
        ("1500", "Equipment", "asset"),
        ("2000", "Accounts Payable", "liability"),
        ("2100", "Loans Payable", "liability"),
        ("3000", "Owner's Equity", "equity"),
        ("3900", "Retained Earnings", "equity"),
        ("4000", "Sales Revenue", "revenue"),
        ("4100", "Service Revenue", "revenue"),
        ("5000", "Cost of Goods Sold", "expense"),
        ("6000", "Rent Expense", "expense"),
        ("6100", "Salaries & Wages", "expense"),
        ("6200", "Utilities Expense", "expense"),
        ("6300", "Office Supplies", "expense"),
        ("6900", "Miscellaneous Expense", "expense"),
    ]
    added = []
    for code, name, type in standard:
        if store.query_one("SELECT id FROM accounts WHERE code = ?", (code,)) is None:
            with store.cursor() as cur:
                cur.execute(
                    "INSERT INTO accounts (code, name, type) VALUES (?, ?, ?)",
                    (code, name, type),
                )
            added.append(code)
    return {"added_codes": added, "skipped_existing": len(standard) - len(added)}


def list_accounts(store: Store) -> dict:
    rows = store.query("SELECT code, name, type FROM accounts ORDER BY code")
    return {
        "accounts": [
            {"code": r["code"], "name": r["name"], "type": r["type"],
             "normal_balance": ACCOUNT_TYPES[r["type"]]}
            for r in rows
        ]
    }


# --------------------------------------------------------------------------- #
# Journal entries
# --------------------------------------------------------------------------- #
def record_journal_entry(store: Store, date: str, lines: list[dict],
                         memo: str = "") -> dict:
    """Record a balanced double-entry journal entry.

    ``lines`` is a list of ``{"account_code": str, "debit": float,
    "credit": float}``. Each line should carry a debit OR a credit (not both),
    and total debits must equal total credits.
    """
    if not lines or len(lines) < 2:
        raise ValueError("A journal entry needs at least two lines.")

    resolved = []
    total_debit = total_credit = 0.0
    for ln in lines:
        code = str(ln.get("account_code", "")).strip()
        acct = _account_by_code(store, code)
        debit = _round(ln.get("debit", 0) or 0)
        credit = _round(ln.get("credit", 0) or 0)
        if debit < 0 or credit < 0:
            raise ValueError("Debit and credit amounts must be non-negative.")
        if debit > 0 and credit > 0:
            raise ValueError(
                f"Line for account {code} has both a debit and a credit; "
                "split it into two lines."
            )
        if debit == 0 and credit == 0:
            raise ValueError(f"Line for account {code} has no debit or credit.")
        resolved.append((acct["id"], debit, credit))
        total_debit += debit
        total_credit += credit

    if abs(total_debit - total_credit) > _TOL:
        raise ValueError(
            f"Entry does not balance: debits {total_debit:.2f} != "
            f"credits {total_credit:.2f}."
        )

    with store.cursor() as cur:
        cur.execute(
            "INSERT INTO journal_entries (date, memo) VALUES (?, ?)",
            (date.strip(), memo.strip()),
        )
        entry_id = cur.lastrowid
        for account_id, debit, credit in resolved:
            cur.execute(
                "INSERT INTO journal_lines (entry_id, account_id, debit, credit) "
                "VALUES (?, ?, ?, ?)",
                (entry_id, account_id, debit, credit),
            )
    return {
        "entry_id": entry_id,
        "date": date.strip(),
        "memo": memo.strip(),
        "total_debit": _round(total_debit),
        "total_credit": _round(total_credit),
        "balanced": True,
    }


def list_journal_entries(store: Store, limit: int = 50) -> dict:
    entries = store.query(
        "SELECT id, date, memo FROM journal_entries ORDER BY date, id DESC LIMIT ?",
        (int(limit),),
    )
    out = []
    for e in entries:
        lines = store.query(
            "SELECT a.code AS code, a.name AS name, l.debit AS debit, l.credit AS credit "
            "FROM journal_lines l JOIN accounts a ON a.id = l.account_id "
            "WHERE l.entry_id = ? ORDER BY l.id",
            (e["id"],),
        )
        out.append({
            "entry_id": e["id"],
            "date": e["date"],
            "memo": e["memo"],
            "lines": [
                {"account_code": ln["code"], "account_name": ln["name"],
                 "debit": _round(ln["debit"]), "credit": _round(ln["credit"])}
                for ln in lines
            ],
        })
    return {"entries": out}


def general_ledger(store: Store, account_code: str) -> dict:
    """Return every posting against one account with a running balance."""
    acct = _account_by_code(store, account_code)
    normal = ACCOUNT_TYPES[acct["type"]]
    rows = store.query(
        "SELECT e.id AS entry_id, e.date AS date, e.memo AS memo, "
        "l.debit AS debit, l.credit AS credit "
        "FROM journal_lines l JOIN journal_entries e ON e.id = l.entry_id "
        "WHERE l.account_id = ? ORDER BY e.date, e.id",
        (acct["id"],),
    )
    running = 0.0
    postings = []
    for r in rows:
        delta = (r["debit"] - r["credit"]) if normal == "debit" else (r["credit"] - r["debit"])
        running += delta
        postings.append({
            "entry_id": r["entry_id"], "date": r["date"], "memo": r["memo"],
            "debit": _round(r["debit"]), "credit": _round(r["credit"]),
            "balance": _round(running),
        })
    return {
        "account": {"code": acct["code"], "name": acct["name"], "type": acct["type"],
                    "normal_balance": normal},
        "postings": postings,
        "ending_balance": _round(running),
    }


def account_balance(store: Store, account_code: str) -> dict:
    acct = _account_by_code(store, account_code)
    normal = ACCOUNT_TYPES[acct["type"]]
    row = store.query_one(
        "SELECT COALESCE(SUM(debit),0) AS d, COALESCE(SUM(credit),0) AS c "
        "FROM journal_lines WHERE account_id = ?",
        (acct["id"],),
    )
    bal = (row["d"] - row["c"]) if normal == "debit" else (row["c"] - row["d"])
    return {
        "code": acct["code"], "name": acct["name"], "type": acct["type"],
        "normal_balance": normal, "balance": _round(bal),
    }


# --------------------------------------------------------------------------- #
# Financial statements
# --------------------------------------------------------------------------- #
def _balances_by_type(store: Store, start: str | None = None, end: str | None = None):
    """Return {account_id: signed_balance} honoring each account's normal side,
    optionally restricted to a date range (inclusive)."""
    where = []
    params: list = []
    if start:
        where.append("e.date >= ?")
        params.append(start)
    if end:
        where.append("e.date <= ?")
        params.append(end)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    rows = store.query(
        f"SELECT a.id AS id, a.code AS code, a.name AS name, a.type AS type, "
        f"COALESCE(SUM(l.debit),0) AS d, COALESCE(SUM(l.credit),0) AS c "
        f"FROM accounts a "
        f"LEFT JOIN journal_lines l ON l.account_id = a.id "
        f"LEFT JOIN journal_entries e ON e.id = l.entry_id {clause} "
        f"GROUP BY a.id ORDER BY a.code",
        tuple(params),
    )
    result = []
    for r in rows:
        normal = ACCOUNT_TYPES[r["type"]]
        bal = (r["d"] - r["c"]) if normal == "debit" else (r["c"] - r["d"])
        result.append({"code": r["code"], "name": r["name"], "type": r["type"],
                       "balance": _round(bal), "debit": _round(r["d"]),
                       "credit": _round(r["c"])})
    return result


def trial_balance(store: Store, as_of: str | None = None) -> dict:
    """List every account with its debit/credit balance and confirm the books tie."""
    rows = _balances_by_type(store, end=as_of)
    total_debit = total_credit = 0.0
    lines = []
    for r in rows:
        normal = ACCOUNT_TYPES[r["type"]]
        bal = r["balance"]
        debit_col = bal if normal == "debit" else 0.0
        credit_col = bal if normal == "credit" else 0.0
        # A negative balance flips columns (e.g. a contra position).
        if bal < 0:
            debit_col, credit_col = (0.0, -bal) if normal == "debit" else (-bal, 0.0)
        total_debit += debit_col
        total_credit += credit_col
        lines.append({"code": r["code"], "name": r["name"], "type": r["type"],
                      "debit": _round(debit_col), "credit": _round(credit_col)})
    return {
        "as_of": as_of,
        "lines": lines,
        "total_debit": _round(total_debit),
        "total_credit": _round(total_credit),
        "in_balance": abs(total_debit - total_credit) <= _TOL,
    }


def income_statement(store: Store, start: str, end: str) -> dict:
    """Profit & Loss for a period: revenue minus expenses = net income."""
    rows = _balances_by_type(store, start=start, end=end)
    revenue = [r for r in rows if r["type"] == "revenue" and r["balance"] != 0]
    expense = [r for r in rows if r["type"] == "expense" and r["balance"] != 0]
    total_rev = _round(sum(r["balance"] for r in revenue))
    total_exp = _round(sum(r["balance"] for r in expense))
    net = _round(total_rev - total_exp)
    return {
        "period": {"start": start, "end": end},
        "revenue": [{"code": r["code"], "name": r["name"], "amount": r["balance"]}
                    for r in revenue],
        "total_revenue": total_rev,
        "expenses": [{"code": r["code"], "name": r["name"], "amount": r["balance"]}
                     for r in expense],
        "total_expenses": total_exp,
        "net_income": net,
        "net_margin_pct": _round(100 * net / total_rev) if total_rev else None,
    }


def balance_sheet(store: Store, as_of: str | None = None) -> dict:
    """Balance sheet as of a date. Current-period earnings (all revenue minus all
    expenses to date) are folded into equity so Assets = Liabilities + Equity."""
    rows = _balances_by_type(store, end=as_of)
    assets = [r for r in rows if r["type"] == "asset" and r["balance"] != 0]
    liabilities = [r for r in rows if r["type"] == "liability" and r["balance"] != 0]
    equity = [r for r in rows if r["type"] == "equity" and r["balance"] != 0]

    total_assets = _round(sum(r["balance"] for r in assets))
    total_liab = _round(sum(r["balance"] for r in liabilities))
    booked_equity = _round(sum(r["balance"] for r in equity))

    net_income = _round(
        sum(r["balance"] for r in rows if r["type"] == "revenue")
        - sum(r["balance"] for r in rows if r["type"] == "expense")
    )
    total_equity = _round(booked_equity + net_income)

    return {
        "as_of": as_of,
        "assets": [{"code": r["code"], "name": r["name"], "amount": r["balance"]}
                   for r in assets],
        "total_assets": total_assets,
        "liabilities": [{"code": r["code"], "name": r["name"], "amount": r["balance"]}
                        for r in liabilities],
        "total_liabilities": total_liab,
        "equity": [{"code": r["code"], "name": r["name"], "amount": r["balance"]}
                   for r in equity]
        + [{"code": "—", "name": "Current Period Earnings", "amount": net_income}],
        "total_equity": total_equity,
        "balances": abs(total_assets - (total_liab + total_equity)) <= _TOL,
        "check": {"liabilities_plus_equity": _round(total_liab + total_equity)},
    }


def cash_flow_statement(store: Store, start: str, end: str,
                        cash_account_code: str = "1000") -> dict:
    """Simplified direct-method cash flow: the net change in the cash account over
    the period, with each cash posting listed. (For a full GAAP statement of cash
    flows you would classify activities as operating/investing/financing.)"""
    acct = _account_by_code(store, cash_account_code)
    opening_row = store.query_one(
        "SELECT COALESCE(SUM(l.debit-l.credit),0) AS net FROM journal_lines l "
        "JOIN journal_entries e ON e.id = l.entry_id "
        "WHERE l.account_id = ? AND e.date < ?",
        (acct["id"], start),
    )
    opening = _round(opening_row["net"])
    rows = store.query(
        "SELECT e.date AS date, e.memo AS memo, l.debit AS debit, l.credit AS credit "
        "FROM journal_lines l JOIN journal_entries e ON e.id = l.entry_id "
        "WHERE l.account_id = ? AND e.date >= ? AND e.date <= ? ORDER BY e.date, e.id",
        (acct["id"], start, end),
    )
    inflows = _round(sum(r["debit"] for r in rows))
    outflows = _round(sum(r["credit"] for r in rows))
    net_change = _round(inflows - outflows)
    return {
        "period": {"start": start, "end": end},
        "cash_account": {"code": acct["code"], "name": acct["name"]},
        "opening_balance": opening,
        "cash_in": inflows,
        "cash_out": outflows,
        "net_change_in_cash": net_change,
        "closing_balance": _round(opening + net_change),
        "movements": [
            {"date": r["date"], "memo": r["memo"],
             "in": _round(r["debit"]), "out": _round(r["credit"])}
            for r in rows
        ],
        "note": "Simplified direct-method view of the cash account, not a "
                "fully classified GAAP statement of cash flows.",
    }
