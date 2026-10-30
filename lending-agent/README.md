# LendAgent

An AI analyst for commercial loan brokers: upload a deal's documents, ask for work in plain
English, and download Excel models and Word loan packages. Built as a side line by two
partners. One partner is a broker who uses it and improves it, and later we sell access to
other brokers.

## Start here: the one-broker start-up version

**[agent/START_HERE.md](agent/START_HERE.md)** covers getting a Claude key, running the app,
and using it on a deal.

```bash
cd agent && pip install -r requirements.txt
ANTHROPIC_API_KEY=sk-ant-... streamlit run broker_app.py
```

| Path | What it is |
|---|---|
| `agent/broker_app.py` | The web page: deals, document upload, chat, downloads |
| `agent/lending_agent/deals.py` | Deal storage and the conversation with Claude |
| `agent/lending_agent/agent.py` | The agent's instructions and tools |
| `agent/lending_agent/underwriting.py` | Loan maths: DSCR, LTV, debt yield, sizing, stress tests |
| `agent/lending_agent/documents.py` | Excel, Word and chart generators |
| `agent/tests/` | Tests (`python -m pytest -q`) |

## Later: selling access to other brokers

These describe the multi-broker version. None of it is needed to start.

- **[PLAN.md](PLAN.md)**: product, roadmap, pricing, costs
- **[SECURITY.md](SECURITY.md)**: how client data is protected once there are many brokers
- **[model/RESULTS.md](model/RESULTS.md)**: financial model for the business
- `infra/terraform/`: AWS servers for the multi-broker version
