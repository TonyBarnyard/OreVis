# LendAgent

An AI analyst for commercial lending, financial planning and legal document work, sold by
subscription. The qualified subscriber makes every lending decision.

- **[PLAN.md](PLAN.md)**: product, capabilities, roadmap, pricing, cost summary, regulatory checklist
- **[SECURITY.md](SECURITY.md)**: how client data is protected
- **[model/RESULTS.md](model/RESULTS.md)**: financial model results (3 scenarios)

## Run things

```bash
# Agent: tests, then a live run (needs ANTHROPIC_API_KEY or AWS Bedrock access)
cd agent && pip install -r requirements.txt && python -m pytest -q
python -m lending_agent.agent "NOI $410k, value $5.2M, request $3.6M at 7.1%, 25-yr am, 10-yr term. Size it, stress it, and write the workbook and memo."

# Financial model: rebuilds the workbook, recalculates every scenario (needs LibreOffice)
cd model && python build_model.py

# Servers
cd infra/terraform && terraform init && terraform plan -var-file=env/staging.tfvars
```
