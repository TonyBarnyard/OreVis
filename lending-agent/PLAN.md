# LendAgent: business and build plan

*Working name. An AI analyst that commercial loan brokers subscribe to.*

## 1. What we're building

LendAgent is a software subscription for **commercial loan brokers**. A broker uploads a
borrower's documents, and the agent does the analyst work: it spreads the financials, sizes the
loan, builds the Excel model, writes the lender-ready package, compares the term sheets that
come back, and keeps the deal checklist current.

**What the business is and isn't:**
- **We sell software.** Brokers pay a flat monthly fee for the AI agent. We take no share of
  their commission, and we don't supply brokers or do the brokering. Each broker is
  responsible for their own licensing and their own deals.
- **We never lend, fund or guarantee loans.** Lenders fund the loans. Brokers place them and
  earn their commission.
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
  The tracker also feeds each broker's monthly value report (section 4).
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

## 3. Roadmap (very lean, slow growth)

| Phase | Months | Deliverables |
|---|---|---|
| 0. Foundations | 1 | Entity, legal review of the broker agreement and disclaimers, AWS setup from Terraform, part-time lending expert engaged |
| 1. MVP | 1–6 | One engineer builds: upload → extract → spread → sizing workbook → lender package for CRE and SBA 7(a); eval set v1 |
| 2. Hardening | 5–8 | Per-account encryption keys, MFA, audit log, SOC 2 Type I via compliance software, pen test, broker profiles, value report |
| 3. Private beta | 7–8 | 5–10 design-partner brokers, free or discounted. Measure hours per deal before and after to prove the value numbers |
| 4. Launch | 9 | Paid plans with a 60-day pilot, Word/Excel add-in. Founder sells and supports the first 25 accounts |
| 5. Grow | 10–24 | Term-sheet comparison, C&I and construction, lender list management; second engineer (month 19); first support hire after 25 accounts; SOC 2 Type II |
| 6. Brokerage firms | 24+ | Multi-broker firm accounts, CRM integrations, single sign-on |

## 4. Pricing: flat monthly fee, priced on value

No share of commission. Each plan is priced so the broker gets **at least 5×** its cost back in
time saved plus the extra loans they can close with that time.

| Plan | Monthly fee | Seats | Time saved / mo | Extra commission / mo* | Value to broker | Broker ROI | % of broker's commission |
|---|---|---|---|---|---|---|---|
| Solo Broker | **$999** | 1 | $3,600 (48 hrs) | $3,750 (+1 loan a quarter) | $7,350 | **7.4×** | 4.4% |
| Broker Team | **$2,499** + $500 onboarding | 3 | $10,800 (144 hrs) | $10,000 (+1 loan every 2 months) | $20,800 | **8.3×** | 3.1% |
| Brokerage Firm | **$6,999** + $2,500 onboarding | 10 | $36,000 (480 hrs) | $25,000 (+1 loan a month) | $61,000 | **8.7×** | 3.5% |

\*Assumes 6 hours saved per deal at $75/hr, 8 deals worked per seat a month, and average loans
of $1.5M / $2M / $2.5M at 1% commission. All of these are inputs in the Pricing sheet, and the
sheet flags any plan that drops below the 5× target.

**Making sure the value is real**
1. **Measure it in the beta.** Time 5–10 design-partner brokers on real deals before and after
   the agent. If they don't save about 6 hours a deal, fix the product or the price before
   launch.
2. **Show it every month.** Each broker gets a value report from the app covering hours saved,
   deals and packages produced, and closings logged. Renewals then rest on numbers, not
   promises.
3. **Lower the risk of trying it.** A 60-day pilot (or the first month free) with cancel-anytime
   terms. Annual prepay gets 2 months free.
4. **Room to raise prices.** At the 5× floor, Solo could go up to about $1,470/mo. Raise prices
   only once the value reports back it up, because higher prices will slow sign-ups.

## 5. What it costs (summary of `model/RESULTS.md`)

The capital below is **operating money for the software company**: salaries, servers, AI
usage and marketing until revenue covers costs. **None of it funds loans.**

**Very lean team:** you (unpaid for the first 24 months, selling and supporting the first 25
brokers), one founding engineer, a lending expert about one day a week, and a fractional
security contractor. A second engineer joins in month 19 and the first support rep after 25
accounts. There are no salespeople or marketing hires.

| Very lean team | **Slow growth (your plan)** | Slow, at earlier $499 pricing | Moderate growth |
|---|---|---|---|
| One-time setup | **$83,400** | $83,400 | $83,400 |
| Spend before the first paying broker (launch month 9) | **$370,000** | $370,000 | $334,000 |
| Peak operating capital needed | **$926,000** | $1.63M | $514,000 |
| Recommended funding (+25% cushion) | **$1.16M** | $2.04M | $643,000 |
| First month with a monthly profit | **35** | beyond 36 | 16 |
| Paying broker accounts, month 12 / 24 / 36 | **8 / 33 / 62** | 8 / 33 / 62 | 21 / 85 / 185 |
| Annual revenue run-rate, month 36 | **$1.46M** | $0.82M | $5.1M |

- **At slow growth, profit arrives near the end of year 3,** so plan funding for about
  $1.2M. Faster sign-ups have the biggest effect: Moderate growth halves the capital needed.
- **The higher prices nearly halve the capital requirement** compared with the earlier
  $499 / $1,499 / $3,999 tiers.
- **Monthly running costs:** servers about $2,950, security and ops software about $1,300,
  and Claude usage about $5.52 per deal analyzed.

## 6. Regulatory and legal checklist (before launch)

Legal review (budgeted at $10k in Setup for the very lean plan) of:

1. **Licensing.** We sell software on a flat monthly fee, take no share of commissions and
   don't broker loans, so we don't expect to need a lending or broker license. The broker
   agreement should state that brokers are responsible for their own licensing, their deals
   and their advice to borrowers.
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
| `model/LendAgent_Financial_Model.xlsx` | The model, shipped as slow growth + very lean team. Scenario in Assumptions!F3, `team_plan` row in Assumptions, prices and value inputs on the Pricing sheet |
| `model/RESULTS.md`, `model_charts.png` | Results of the last run |
