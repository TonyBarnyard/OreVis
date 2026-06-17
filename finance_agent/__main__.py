"""Interactive CLI for the accounting & financial-advising agent.

Run with:  python -m finance_agent
Requires the ANTHROPIC_API_KEY environment variable.
"""

from __future__ import annotations

import os
import sys

# Load a .env file if python-dotenv is installed (optional convenience).
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

from .agent import MODEL, FinanceAgent
from .store import DEFAULT_DB, Store

BANNER = f"""\
\033[1mLedger — AI Accounting & Financial Advising Agent\033[0m
Model: {MODEL}   Ledger DB: {DEFAULT_DB}

I can keep your books (double-entry ledger, journal entries, P&L, balance
sheet, cash flow) and advise on budgeting, investing, loans, retirement, and
taxes. Everything is computed with real tools and saved to a local database.

Commands:  /help   /reset   /accounts   /db   /exit
Type a question or describe a transaction to get started.
"""

HELP = """\
Examples you can try:
  • "Set up a fresh set of books for my consulting business."
  • "Record: on 2026-01-15 I invoiced a client $4,000 for services, unpaid."
  • "Show me a profit & loss for January 2026."
  • "What's my balance sheet?"
  • "I make $7,500/month after tax. Rent 2200, groceries 600, car 450,
     subscriptions 120, dining 500. How's my budget?"
  • "If I invest $500/month at 7% for 30 years, what do I end up with?"
  • "Amortize a $350,000 mortgage at 6.25% over 30 years."
  • "Estimate my 2025 federal tax: single, $120,000 gross, $10k to 401k."
  • "Can I retire at 60? I'm 35, have $80k saved, add $1,500/month at 6.5%,
     and want $60k/year in retirement."

Commands:
  /help      show this help
  /reset     clear the conversation (the ledger is kept)
  /accounts  list the chart of accounts
  /db        show the ledger database path
  /exit      quit
"""


def main() -> int:
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print(
            "Error: set ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN) in your "
            "environment or a .env file.",
            file=sys.stderr,
        )
        return 1

    store = Store()
    agent = FinanceAgent(store=store)
    print(BANNER)

    while True:
        try:
            user = input("\n\033[1myou ›\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user:
            continue
        cmd = user.lower()
        if cmd in ("/exit", "/quit", "exit", "quit"):
            print("Goodbye.")
            break
        if cmd == "/help":
            print(HELP)
            continue
        if cmd == "/reset":
            agent.reset()
            print("Conversation cleared. The ledger is unchanged.")
            continue
        if cmd == "/db":
            print(f"Ledger database: {os.path.abspath(store.path)}")
            continue
        if cmd == "/accounts":
            from .accounting import list_accounts

            accts = list_accounts(store)["accounts"]
            if not accts:
                print("No accounts yet. Ask me to set up a chart of accounts.")
            else:
                for a in accts:
                    print(f"  {a['code']:>6}  {a['name']:<28} {a['type']}")
            continue

        print("\n\033[1mLedger ›\033[0m ", end="")
        try:
            agent.send(user)
        except Exception as e:  # keep the REPL alive on API/tool errors
            print(f"\n[error: {type(e).__name__}: {e}]")

    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
