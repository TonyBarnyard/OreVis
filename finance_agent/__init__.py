"""finance_agent — a standalone AI agent for accounting and financial advising.

Powered by the Anthropic Claude API. The language model orchestrates a set of
deterministic tools that do the actual bookkeeping (a double-entry ledger backed
by SQLite) and the actual financial math (amortization, projections, tax
estimates, etc.), so numbers are computed in code rather than guessed.
"""

__version__ = "0.1.0"
