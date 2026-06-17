# Ledger — AI Accounting & Financial Advising Agent

A single, standalone agent that does **both** jobs:

- **Accountant / bookkeeper** — maintains a real **double-entry general ledger**
  in a local SQLite database: chart of accounts, journal entries (debits must
  equal credits), trial balance, income statement (P&L), balance sheet, cash
  flow, and per-account general ledgers.
- **Financial advisor / planner** — budgeting (50/30/20), investment growth
  projections, savings goals, loan & mortgage amortization, retirement
  accumulation + drawdown modeling, U.S. federal tax estimates, net worth, and
  business financial ratios.

The Claude model orchestrates the conversation, but **every number is computed
by a deterministic Python tool** and every change to the books is persisted —
so the math is exact and auditable, not guessed.

## How it works

```
You ──▶ Ledger agent (Claude, claude-opus-4-8)
            │  picks and calls tools
            ▼
   ┌─────────────────────┬──────────────────────────┐
   │ accounting.py       │ advising.py               │
   │ (double-entry book- │ (loans, projections, tax, │
   │  keeping + reports)  │  budgets, ratios …)       │
   └─────────┬───────────┴──────────────────────────┘
             ▼
        SQLite ledger (finance_agent.db)
```

Built on the official Anthropic Python SDK with a streaming, manual tool-use
loop (`agent.py`). Tools are defined in `tools.py`; the system prompt that
defines the dual role is in `prompts.py`.

## Setup

```bash
cd finance_agent          # this directory
pip install -r requirements.txt
cp .env.example .env      # then add your ANTHROPIC_API_KEY
```

Get an API key at https://console.anthropic.com/.

## Run

From the repository root (the directory **above** `finance_agent/`):

```bash
python -m finance_agent
```

You'll get an interactive prompt. Try:

- "Set up a fresh set of books for my consulting business."
- "Record: on 2026-01-15 I invoiced a client $4,000 for services, unpaid."
- "Show me a P&L for January 2026, then my balance sheet."
- "I take home $7,500/month. Rent 2200, groceries 600, car 450, dining 500.
  How's my budget?"
- "Amortize a $350,000 mortgage at 6.25% over 30 years with $200 extra/month."
- "Can I retire at 60? I'm 35, have $80k saved, add $1,500/month at 6.5%,
  and want $60k/year in retirement."
- "Estimate my 2025 federal tax: single, $120,000 gross, $10k to 401(k)."

CLI commands: `/help`, `/reset`, `/accounts`, `/db`, `/exit`.

## Verify without an API key

The deterministic tools (ledger + financial math) have an offline self-test:

```bash
python -m finance_agent.selftest
```

## Configuration

| Variable             | Default             | Purpose                          |
| -------------------- | ------------------- | -------------------------------- |
| `ANTHROPIC_API_KEY`  | —                   | Required. Your Anthropic key.    |
| `FINANCE_MODEL`      | `claude-opus-4-8`   | Claude model to use.             |
| `FINANCE_DB`         | `finance_agent.db`  | Path to the local ledger DB.     |

## Tools at a glance

**Accounting:** `seed_standard_chart`, `add_account`, `list_accounts`,
`record_journal_entry`, `list_journal_entries`, `general_ledger`,
`account_balance`, `trial_balance`, `income_statement`, `balance_sheet`,
`cash_flow_statement`.

**Advising:** `loan_amortization`, `investment_projection`, `savings_goal`,
`retirement_projection`, `budget_analysis`, `net_worth`, `tax_estimate`,
`financial_ratios`.

**Memory:** `set_profile`, `get_profile` (remembers client/business context).

## Scope & disclaimers

This agent provides **education, bookkeeping, and analysis**. It is **not** a
substitute for a licensed CPA, CFP, or attorney, and it does not file returns.
Tax figures are **simplified U.S. federal estimates** (no FICA, state/local
tax, or credits). Investment projections are estimates, not guarantees. For
binding tax, legal, or regulated investment decisions, consult a licensed
professional. Default currency is USD.
