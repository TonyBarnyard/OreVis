# LendAgent: business and build plan

*Working name. An AI analyst sold by subscription to commercial-lending professionals.*

## 1. What we're building

LendAgent is an AI analyst for commercial-lending professionals: loan brokers, originators,
credit analysts at community banks and credit unions, SBA lenders, private lenders, and the
financial advisors and attorneys who work with them. It takes in a loan package, does the
analyst work, and returns finished work product in Word and Excel. **The subscriber makes every
credit decision.** The agent never approves, declines or prices a loan.

| The subscriber does | LendAgent does |
|---|---|
| Decides on the loan, the structure and the price | Spreads financials and tax returns, computes cash flow and ratios |
| Holds the license and the client relationship | Drafts credit memos, term sheets, checklists and client emails |
| Signs off on every document | Builds Excel models with live formulas, charts and stress tests |
| Sets credit policy (min DSCR, max LTV, etc.) | Flags policy exceptions, missing documents and inconsistencies |

### Capability map

**Commercial-lending analysis**
- Spreading tax returns and statements: Forms 1040/Sch. C/E, 1120, 1120-S, 1065, K-1s, P&Ls,
  balance sheets, AR/AP agings, rent rolls, T-12s, personal financial statements.
- Underwriting math (deterministic code in `agent/lending_agent/underwriting.py`, never done
  by the model in its head): DSCR, global cash flow, LTV/LTC, debt yield, break-even occupancy,
  loan sizing across all constraints, amortization and balloon schedules, rate-shock and
  NOI-decline stress tests.
- Loan types: CRE (investor and owner-occupied), C&I lines and term loans, SBA 7(a)/504,
  equipment, construction/bridge, multifamily, hospitality.
- Collateral and third-party report review: appraisals, environmental Phase I, title
  commitments, surveys, insurance, leases and estoppels.

**Financial planning**
- Business cash-flow forecasts, debt capacity, refinance vs. hold analysis, owner exit and
  succession scenarios, personal liquidity and guarantor strength.

**Legal document support** (information for a professional's review, not legal advice)
- Summarize and compare term sheets, commitment letters, loan agreements, guaranties,
  intercreditor agreements, UCC filings and leases. Extract covenants into a tracker. Draft
  closing checklists and condition lists. Every signed document goes to counsel.

**Office output**
- **Excel / Google Sheets:** sizing models, spreads, sensitivity tables, covenant trackers,
  pipeline lists, all with live formulas.
- **Word / Google Docs:** credit memos, term-sheet drafts, borrower request letters,
  annual-review memos.
- **Charts and graphs:** DSCR trends, rate-shock curves, rent-roll expirations, cash-flow
  waterfalls, portfolio concentration.
- **Lists and trackers:** document checklists, condition lists, exception logs, pipeline boards.

### How it's tailored to each subscriber

Each account loads its own **policy pack** at onboarding: credit policy limits, approved memo
template, house spreading conventions, preferred term-sheet language, state-specific closing
requirements. The agent applies the pack to every deal. Packs ship pre-built for common
profiles (SBA lender, community bank CRE, bridge lender, broker) and are tuned by our lending
SME during onboarding.

## 2. How the agent is built

```
 Subscriber (web app, Word/Excel add-in)
        │  SSO + MFA
        ▼
 ┌─────────── API service (ECS Fargate, private subnets) ───────────┐
 │  tenant auth · deal workspaces · policy packs · audit log        │
 └───────┬───────────────────────────┬──────────────────────────────┘
         │ jobs                      │ row-level-security Postgres (pgvector)
         ▼                           ▼
 ┌──── Worker service ────┐    ┌──── Data ─────────────────────────┐
 │ 1 OCR scanned pages    │    │ S3: documents, per-tenant KMS key │
 │ 2 Extract (Haiku 5.5)  │    │ RDS: deals, spreads, embeddings   │
 │ 3 Analyze (Opus 5.5)   │──► │ Audit bucket (Object Lock WORM)   │
 │   + calc/doc tools     │    └───────────────────────────────────┘
 │ 4 Write xlsx/docx/png  │
 └──────────┬─────────────┘
            │ PrivateLink (no public internet)
            ▼
   Claude on Amazon Bedrock (or Anthropic API under zero data retention)
```

- **Model routing.** Claude Haiku 5.5 handles high-volume page extraction (about $0.06 per
  deal). Claude Opus 5.5 handles analysis, the credit memo and the workbook (about $4.40 per
  deal before buffer). Claude Sonnet 5.5 handles everyday drafting and chat. Prompt caching
  keeps the large policy pack and document context cheap across turns.
- **Tools, not guesses.** Every number in a deliverable comes from a calculation tool, with
  the source document and page cited. The starter tool set is in `agent/lending_agent/agent.py`.
- **Guardrails in the system prompt and the code:** no credit decisions, ECOA/Reg B
  prohibited-basis data excluded from analysis, legal content framed as information, and
  uploaded documents treated as data, never as instructions (prompt-injection defense).
- **Quality.** We build an evaluation set of synthetic loan packages with known-correct
  spreads and memos, graded by our lending SME. Every prompt or model change must pass it
  before release.

## 3. Roadmap

| Phase | Months | Deliverables |
|---|---|---|
| 0. Foundations | 1 | Entity, regulatory counsel memo, AWS org + Terraform baseline, hire SME |
| 1. MVP | 1–4 | Upload → extract → spread → sizing workbook → credit memo for CRE and SBA 7(a); eval set v1 |
| 2. Hardening | 4–6 | Per-tenant KMS keys, SSO/MFA, audit log, SOC 2 Type I readiness, pen test, policy packs |
| 3. Private beta | 5–6 | 10–15 design partners (brokers + 2–3 community lenders), free or discounted |
| 4. Launch | 7 | Paid plans, Word/Excel add-in, Google Workspace export, onboarding playbook |
| 5. Expand | 8–18 | C&I, construction, covenant monitoring, annual reviews, portfolio dashboards; SOC 2 Type II (month ~13) |
| 6. Enterprise | 12–24 | Bank/CU tier: core and LOS integrations (nCino, Encompass, Abrigo), SSO/SCIM, dedicated-key option, vendor-risk package |

## 4. Pricing

Pricing is a flat subscription per account. It is set as a small share of the commission or fee
income the subscriber expects to earn, and well below the analyst time it saves (see
`model/` → Pricing sheet).

| Plan | Price | Seats | For | Expected monthly commission* | Price as % of commission |
|---|---|---|---|---|---|
| Starter | **$499/mo** | 1 | Solo broker or advisor | $22,500 (1.5 loans × $1.5M × 1%) | 2.2% |
| Professional | **$1,499/mo** + $500 onboarding | 3 | Brokerage / advisory team | $80,000 (4 × $2M × 1%) | 1.9% |
| Enterprise | **from $4,500/mo** + $5,000 onboarding | 10 | Bank, CU, private lender | $270,000 (12 × $3M × 0.75%) | 1.7% |

\*Illustrative assumptions. Change them in the Pricing sheet.

- Annual prepay: 2 months free (improves cash flow, lowers churn).
- Usage add-on: extra deal workspaces beyond the plan allowance at about $49 each, which
  protects margin from very heavy users.
- Time saved alone pays for the plan 7× or more (about 6 analyst hours saved per deal at
  $75–85/hr).
- **Why not charge a percentage of commission?** Taking a share of loan fees can make us look
  like a broker or finder under some state lending laws (for example the California Financing
  Law). It can also create licensing and conflict-of-interest questions, and it ties our
  revenue to loans closing, which the subscriber controls. Use commission as the *yardstick*
  for setting the price, not as the billing basis, unless regulatory counsel signs off.

## 5. What it costs (summary of `model/RESULTS.md`)

| | Conservative | **Base** | Aggressive |
|---|---|---|---|
| One-time setup (legal, SOC 2, pen test, brand, equipment, 15% contingency) | $211,600 | **$211,600** | $211,600 |
| Spend before the first paying customer | $847,730 | **$739,250** | $590,770 |
| Peak capital required | $5.31M | **$2.83M** | $1.32M |
| Recommended raise (+25% cushion) | $6.6M | **$3.5M** | $1.6M |
| First EBITDA-positive month | beyond 36 | **28** | 17 |
| Paying accounts, month 36 | 177 | **548** | 1,545 |
| ARR, month 36 | $2.9M | **$9.9M** | $30.4M |
| Gross margin, year 3 | 64% | **72%** | 75% |

Monthly running costs:

- **Servers (AWS, production + staging + DR):** about $2,950/mo.
- **Security and operations SaaS:** about $3,800/mo.
- **Claude usage:** about $5.52 per deal analyzed, or roughly $160 per account per month at
  base usage.
- **Support:** one customer-success rep per 60 accounts (about $8,500/mo each).

**Where the money goes (months 1–27, base case):** payroll 52%, sales and marketing 21%,
support staff 6%, Claude usage 6%, one-time setup 3%, servers 1%. Servers and AI aren't what
drive the capital need. People and customer acquisition are, so hiring pace (Staffing sheet)
and CAC are the levers to pull if you want to raise less.

**Ways to lower the capital requirement:** founder takes no salary in year 1 (−$150k),
delay the second AE and the compliance manager, use a fractional SME, and sell annual
prepay to design partners. Then re-run `python model/build_model.py`.

## 6. Regulatory and legal checklist (before launch)

Get regulatory counsel's opinion (budgeted at $25k in Setup) on:

1. **Licensing.** Confirm that a software subscription with no share of loan fees doesn't
   require broker or lender licensing in our target states.
2. **ECOA / Reg B and fair lending.** We exclude prohibited-basis data from analysis, the
   subscriber makes the decision, and we keep explainable, logged reasoning. If we ever
   generate adverse-action reasons, subscribers must be able to review them.
3. **Unauthorized practice of law.** Legal features summarize and draft for review by
   professionals and counsel. They don't give legal advice to borrowers.
4. **GLBA.** Subscribers are financial institutions. We are their *service provider* under the
   GLBA Safeguards Rule and Privacy Rule, which flows into our contracts (DPA) and security
   program (`SECURITY.md`).
5. **Bank vendor-risk requirements.** Interagency third-party risk guidance (OCC/Fed/FDIC
   2023) means bank and credit-union customers will run vendor due diligence. Have a SOC 2
   report, pen-test letter, BCP/DR plan and the SIG-Lite questionnaire ready.
6. **State privacy laws and AI-use disclosures.** Cover CCPA/CPRA and similar laws, plus
   disclosure of AI use in the terms of service and in generated documents.

## 7. Repository map

| Path | What it is |
|---|---|
| `PLAN.md` | This plan |
| `SECURITY.md` | Client-data protection strategy |
| `infra/terraform/` | AWS servers: network, database, document storage, compute, WAF, monitoring, DR |
| `agent/` | Agent code: Claude tool runner, underwriting math, Excel/Word/chart generators, tests |
| `model/build_model.py` | Builds and runs the financial model |
| `model/LendAgent_Financial_Model.xlsx` | The model: all formulas, scenario selector in Assumptions!F3 |
| `model/RESULTS.md`, `model_charts.png` | Results of the last run, all three scenarios |
