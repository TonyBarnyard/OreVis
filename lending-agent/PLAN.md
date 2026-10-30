# LendAgent: business and build plan

*Working name. An AI analyst that commercial loan brokers subscribe to.*

## 1. What we're building

LendAgent is a software subscription for **commercial loan brokers**. A broker uploads a
borrower's documents, and the agent does the analyst work: it spreads the financials, sizes the
loan, builds the Excel model, writes the lender-ready package, compares the term sheets that
come back, and keeps the deal checklist current.

**What the business is and isn't:**
- **We sell software.** Our revenue is monthly subscriptions paid by brokers.
- **We never lend, fund or guarantee loans,** and we don't take a share of loan fees. Lenders
  fund the loans. Brokers place them and earn their commission.
- **We don't make decisions.** Lenders make the credit decision. The broker decides what to
  recommend to the borrower and what to submit to which lender. The agent prepares the analysis
  and the documents.

| The broker does | LendAgent does |
|---|---|
| Owns the borrower relationship and holds any required license | Spreads tax returns and financials, computes cash flow and ratios |
| Decides which lenders to approach and what to recommend | Sizes the loan against typical lender limits (DSCR, LTV, debt yield) |
| Submits the package and negotiates terms | Builds the lender-ready package, executive summary and Excel model |
| Signs off on everything that leaves the office | Compares lender term sheets side by side and flags differences |
| Earns the commission | Tracks documents, conditions and the deal pipeline |

### Capability map

**Commercial-lending analysis**
- Spreading tax returns and statements: Forms 1040/Sch. C/E, 1120, 1120-S, 1065, K-1s, P&Ls,
  balance sheets, AR/AP agings, rent rolls, T-12s, personal financial statements.
- Underwriting math (deterministic code in `agent/lending_agent/underwriting.py`, never done
  by the model in its head): DSCR, global cash flow, LTV/LTC, debt yield, break-even occupancy,
  loan sizing across all constraints, amortization and balloon schedules, rate-shock and
  NOI-decline stress tests.
- Pre-screening: spot the issues a lender's underwriter will raise (weak coverage, thin
  liquidity, inconsistent figures, missing documents) so the broker can fix them before
  submitting.
- Loan types: CRE (investor and owner-occupied), C&I lines and term loans, SBA 7(a)/504,
  equipment, construction/bridge, multifamily, hospitality.

**Broker workflow**
- Lender-ready loan packages: executive summary, sources and uses, borrower and guarantor
  profile, collateral summary, financial spreads, and a document index.
- Side-by-side comparison of lender term sheets: rate, fees, amortization, prepayment,
  recourse and covenants, with the borrower's effective cost under each.
- Borrower intake checklists and document-request emails. Deal pipeline and commission tracker.
- Lender-fit notes against the broker's own lender list and criteria (the broker maintains
  the list, and the agent applies it).

**Financial planning**
- Business cash-flow forecasts, debt capacity, refinance vs. hold analysis, owner exit and
  succession scenarios, personal liquidity and guarantor strength.

**Legal document support** (information for a professional's review, not legal advice)
- Summarize and compare term sheets, commitment letters, loan agreements, guaranties, UCC
  filings and leases. Extract covenants into a tracker. Draft closing checklists. Every signed
  document goes to counsel.

**Office output**
- **Excel / Google Sheets:** sizing models, spreads, sensitivity tables, term-sheet
  comparisons, pipeline and commission lists, all with live formulas.
- **Word / Google Docs:** loan packages, executive summaries, borrower letters, memos.
- **Charts and graphs:** DSCR trends, rate-shock curves, rent-roll expirations, cash-flow
  waterfalls, pipeline by stage.

### Tailoring to each broker

Each account sets up a **broker profile** at onboarding: specialties (SBA, CRE, equipment and
so on), the broker's lender list with each lender's typical limits, preferred package layout
and branding, and standard borrower-request language. The agent applies it to every deal. Our
lending expert configures it during onboarding.

## 2. How the agent is built

```
 Broker (web app, Word/Excel add-in)
        │  sign-in with MFA
        ▼
 ┌─────────── API service (ECS Fargate, private subnets) ───────────┐
 │  account auth · deal workspaces · broker profiles · audit log    │
 └───────┬───────────────────────────┬──────────────────────────────┘
         │ jobs                      │ row-level-security Postgres (pgvector)
         ▼                           ▼
 ┌──── Worker service ────┐    ┌──── Data ──────────────────────────┐
 │ 1 OCR scanned pages    │    │ S3: documents, per-account KMS key │
 │ 2 Extract (Haiku 5.5)  │    │ RDS: deals, spreads, embeddings    │
 │ 3 Analyze (Opus 5.5)   │──► │ Audit bucket (Object Lock WORM)    │
 │   + calc/doc tools     │    └────────────────────────────────────┘
 │ 4 Write xlsx/docx/png  │
 └──────────┬─────────────┘
            │ PrivateLink (no public internet)
            ▼
   Claude on Amazon Bedrock (or Anthropic API under zero data retention)
```

- **Model routing.** Claude Haiku 5.5 handles high-volume page extraction (about $0.06 per
  deal). Claude Opus 5.5 handles analysis, the package and the workbook (about $4.40 per deal
  before buffer). Claude Sonnet 5.5 handles everyday drafting and chat. Prompt caching keeps
  the broker profile and document context cheap across turns.
- **Tools, not guesses.** Every number in a deliverable comes from a calculation tool, with
  the source document and page cited. The starter tool set is in `agent/lending_agent/agent.py`.
- **Guardrails:** no credit decisions or recommendations, ECOA/Reg B prohibited-basis data
  excluded from analysis, legal content framed as information, and uploaded documents treated
  as data, never as instructions.
- **Quality.** We build an evaluation set of synthetic loan packages with known-correct
  spreads, graded by our lending expert. Every prompt or model change must pass it before
  release.

## 3. Roadmap

| Phase | Months | Deliverables |
|---|---|---|
| 0. Foundations | 1 | Entity, regulatory counsel memo, AWS setup from Terraform, lending expert engaged |
| 1. MVP | 1–4 | Upload → extract → spread → sizing workbook → lender package for CRE and SBA 7(a); eval set v1 |
| 2. Hardening | 4–6 | Per-account encryption keys, MFA, audit log, SOC 2 Type I readiness, pen test, broker profiles |
| 3. Private beta | 5–6 | 10–15 design-partner brokers, free or discounted |
| 4. Launch | 7 | Paid plans, Word/Excel add-in, Google Workspace export, onboarding playbook |
| 5. Expand | 8–18 | Term-sheet comparison, pipeline and commission tracker, C&I and construction, lender list management; SOC 2 Type II (month ~13) |
| 6. Brokerage firms | 12–24 | Multi-broker firm accounts, CRM integrations (Salesforce, HubSpot), shared lender lists, single sign-on |

## 4. Pricing

Pricing is a flat monthly subscription per broker account. It's sized at about 2% of the
commission the broker expects to earn, and well below the analyst time it saves (see `model/`
→ Pricing sheet).

| Plan | Price | Seats | For | Expected monthly commission* | Price as % of commission |
|---|---|---|---|---|---|
| Solo Broker | **$499/mo** | 1 | Independent commercial loan broker | $22,500 (1.5 loans × $1.5M × 1%) | 2.2% |
| Broker Team | **$1,499/mo** + $500 onboarding | 3 | Broker with partners or analysts | $80,000 (4 × $2M × 1%) | 1.9% |
| Brokerage Firm | **$3,999/mo** + $2,500 onboarding | 10 | Firm of up to 10 brokers | $200,000 (8 × $2.5M × 1%) | 2.0% |

\*Illustrative assumptions. Change them in the Pricing sheet.

- Annual prepay: 2 months free (improves cash flow, lowers churn).
- Usage add-on: extra deal workspaces beyond the plan allowance at about $49 each.
- Time saved alone pays for the plan about 7× (about 6 hours saved per deal at $75/hr).
- **Why a flat fee, not a percentage of the broker's commission?** Taking a share of loan fees
  can make *us* look like a broker or finder under some state lending laws (for example the
  California Financing Law), which could require us to be licensed. Use commission as the
  yardstick for setting the price, not as what you bill, unless regulatory counsel signs off.

## 5. What it costs (summary of `model/RESULTS.md`)

The capital below is **operating money for the software company**: salaries, servers, AI
usage and marketing until subscription revenue covers costs. **None of it funds loans.**

| Base case | Full team | Lean founder-led team |
|---|---|---|
| One-time setup (legal, SOC 2, pen test, brand, equipment, 15% contingency) | $211,600 | $211,600 |
| Spend before the first paying broker (6 months) | $739,250 | $496,250 |
| Peak operating capital needed | $3.13M | **$1.87M** |
| Recommended funding (+25% cushion) | $3.9M | **$2.3M** |
| First month with a monthly profit | 30 | 29 |
| Paying broker accounts, month 36 | 548 | 548 |
| Annual recurring revenue, month 36 | $9.4M | $9.4M |

Other scenarios: the conservative case needs $4.1–5.5M and isn't profitable within 36 months.
The aggressive case needs $0.8–1.5M and turns a monthly profit by month 15–18. Both team plans
assume the same growth, and a leaner team may in practice grow more slowly.

Monthly running costs:

- **Servers (AWS: production, staging and disaster-recovery copy):** about $2,950/mo.
- **Security and operations software:** about $3,800/mo.
- **Claude usage:** about $5.52 per deal analyzed, or roughly $160 per broker account per month.
- **Support:** one customer-success rep per 60 accounts (about $8,500/mo each).

**Where the money goes:** payroll is about half, and sales and marketing about a fifth.
Servers (about 1%) and AI usage (about 6%) are small. Hiring pace and the cost to win each
broker are the levers that move the capital requirement. Both are inputs in the spreadsheet
(Staffing sheet, and `team_plan` and CAC in Assumptions).

## 6. Regulatory and legal checklist (before launch)

Get regulatory counsel's opinion (budgeted at $25k in Setup) on:

1. **Our own licensing.** Confirm that a flat software subscription, with no share of loan
   fees and no lender referrals, doesn't require broker, lender or finder licensing in our
   target states. Brokers remain responsible for their own licenses.
2. **ECOA / Reg B and fair lending.** We exclude prohibited-basis data from analysis, and
   lenders make the credit decisions.
3. **Unauthorized practice of law.** Legal features summarize and draft for review by
   professionals and counsel. They don't advise borrowers.
4. **GLBA and privacy.** Brokers collect guarantors' personal financial information (tax
   returns, personal financial statements, SSNs). Treat it as nonpublic personal information
   under the FTC Safeguards Rule, and commit to it in our DPA and security program
   (`SECURITY.md`).
5. **Lender requirements.** Some lenders ask brokers how borrower data is handled. Have a
   SOC 2 report and a short security summary that brokers can share.
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
| `model/LendAgent_Financial_Model.xlsx` | The model. Scenario in Assumptions!F3, team plan in Assumptions (`team_plan`) |
| `model/RESULTS.md`, `model_charts.png` | Results of the last run: every scenario, both team plans |
