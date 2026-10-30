"""Build the LendAgent business financial model as a formula-driven Excel workbook.

Every output in the workbook is an Excel formula over the input cells, so you can
change any blue number in Excel/Sheets and the whole model updates. This script
also recalculates the workbook under each scenario (LibreOffice) and writes the
headline results to results.json / RESULTS.md.

    python build_model.py            # writes LendAgent_Financial_Model.xlsx + results
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent
OUT = HERE / "LendAgent_Financial_Model.xlsx"
MONTHS = 36
FIRST_COL = 3  # month 1 lives in column C of the Monthly sheet

FONT = "Arial"
F_INPUT = Font(name=FONT, color="0000FF")
F_LINK = Font(name=FONT, color="008000")
F_BODY = Font(name=FONT)
F_BOLD = Font(name=FONT, bold=True)
F_TITLE = Font(name=FONT, bold=True, size=14)
F_NOTE = Font(name=FONT, italic=True, color="666666", size=9)
FILL_KEY = PatternFill("solid", start_color="FFFF00")
FILL_HEAD = PatternFill("solid", start_color="D9E1F2")

USD = '$#,##0;($#,##0);"-"'
USD2 = '$#,##0.00;($#,##0.00);"-"'
NUM = '#,##0;(#,##0);"-"'
NUM1 = '#,##0.0;(#,##0.0);"-"'
PCT = '0.0%;(0.0%);"-"'
MULT = '0.0"x"'


def style(cell, font=F_BODY, fmt=None, fill=None):
    cell.font = font
    if fmt:
        cell.number_format = fmt
    if fill:
        cell.fill = fill
    return cell


def title(ws, text, subtitle=None):
    style(ws["A1"], F_TITLE).value = text
    if subtitle:
        style(ws["A2"], F_NOTE).value = subtitle


# ---------------------------------------------------------------- Assumptions
# key, label, format, conservative, base, aggressive, source/note
SCENARIO_INPUTS = [
    ("Timing", None),
    ("launch_month", "First paid month (earlier months = build + private beta)", NUM, 8, 7, 6,
     "Plan: 6-month MVP build incl. SOC 2 Type I readiness; see PLAN.md roadmap."),
    ("Customer growth", None),
    ("new_at_launch", "New paying accounts in launch month", NUM1, 4, 6, 10,
     "Founder-led sales from beta waitlist; assumption to validate in beta."),
    ("new_growth", "Monthly growth in new-account adds", PCT, 0.05, 0.08, 0.10,
     "Assumption. Typical early vertical SaaS 5-12%/mo."),
    ("new_cap", "Cap on new accounts per month", NUM, 50, 90, 150,
     "Sales/onboarding capacity ceiling."),
    ("churn", "Monthly account churn", PCT, 0.035, 0.025, 0.018,
     "Assumption. SMB vertical SaaS commonly 2-4%/mo."),
    ("Plan mix (share of new accounts)", None),
    ("mix_starter", "Starter (solo) share", PCT, 0.50, 0.45, 0.40, "Assumption."),
    ("mix_pro", "Professional (team) share", PCT, 0.38, 0.40, 0.42, "Assumption."),
    ("mix_ent", "Enterprise (lender) share", PCT, 0.12, 0.15, 0.18,
     "Assumption. Shares must total 100%."),
    ("Usage", None),
    ("deals_per_seat", "Deals analyzed per seat per month", NUM1, 10, 8, 8,
     "Assumption: pipeline deals worked (not closed). Higher usage = higher AI cost."),
    ("Support & acquisition", None),
    ("accts_per_csm", "Accounts per customer-success/support rep", NUM, 50, 60, 75,
     "Assumption for high-touch B2B onboarding."),
    ("cac", "Customer acquisition cost per new account ($)", USD, 6000, 4000, 2500,
     "Assumption: paid search/LinkedIn, events, referral fees. AE and marketing salaries are "
     "in Staffing, so fully loaded CAC is higher. Validate after launch."),
]

FIXED_INPUTS = [
    ("Costs (all scenarios)", None),
    ("csm_cost", "Customer success rep, loaded monthly cost ($)", USD, 8500,
     "~$80k salary x 1.25 burden / 12."),
    ("base_marketing", "Base marketing spend per month ($), from 2 months pre-launch", USD, 5000,
     "Content, website, conferences (e.g. state broker associations, NAGGL, CREFC)."),
    ("payment_pct", "Card/ACH processing as % of revenue", PCT, 0.029,
     "Stripe list price 2.9% + $0.30 (ACH cheaper)."),
    ("infra_var_seat", "Variable hosting per seat per month ($)", USD, 12,
     "Storage, egress, worker compute, embeddings. Estimate."),
    ("kms_per_account", "Per-tenant encryption key per account per month ($)", USD, 1,
     "AWS KMS customer-managed key $1/key/month."),
    ("build_infra_factor", "Hosting during build as % of production baseline", PCT, 0.4,
     "Staging + small prod before launch."),
    ("insurance", "Insurance per month: cyber, tech E&O, D&O ($)", USD, 2500,
     "Estimate; quotes vary with limits ($3-5M cyber/E&O typical for fintech vendors)."),
    ("prof_services", "Accounting, bookkeeping, legal retainer per month ($)", USD, 4500,
     "Estimate."),
    ("compliance_recurring", "SOC 2 Type II + annual pen test + audits, per month ($)", USD, 5000,
     "~$60k/yr once on annual SOC 2 Type II cycle."),
    ("compliance_start", "Month recurring compliance costs begin", NUM, 13, "After Type I."),
    ("ga_other", "Other G&A per month ($): software seats, travel, co-working", USD, 3000,
     "Estimate."),
]


def build_assumptions(wb):
    ws = wb.create_sheet("Assumptions")
    title(ws, "Assumptions",
          "Blue = input you can change. Yellow = scenario selector. Column F feeds the model.")
    style(ws["A3"], F_BOLD).value = "Scenario (1 = Conservative, 2 = Base, 3 = Aggressive)"
    style(ws["F3"], F_INPUT, NUM, FILL_KEY).value = 2
    style(ws["G3"], F_BODY).value = '=CHOOSE($F$3,"Conservative","Base","Aggressive")'
    for col, h in zip("ACDEFG", ["Assumption", "Conservative", "Base", "Aggressive",
                                 "Selected", "Source / note"]):
        style(ws[f"{col}5"], F_BOLD, fill=FILL_HEAD).value = h
    refs = {}
    r = 6
    for item in SCENARIO_INPUTS:
        if item[1] is None:
            style(ws.cell(r, 1), F_BOLD).value = item[0]
            r += 1
            continue
        key, label, fmt, c, b, a, note = item
        ws.cell(r, 1, label).font = F_BODY
        for col, v in zip((3, 4, 5), (c, b, a)):
            style(ws.cell(r, col), F_INPUT, fmt).value = v
        style(ws.cell(r, 6), F_BODY, fmt).value = f"=CHOOSE($F$3,C{r},D{r},E{r})"
        style(ws.cell(r, 7), F_NOTE).value = note
        refs[key] = f"Assumptions!$F${r}"
        r += 1
    r += 1
    for item in FIXED_INPUTS:
        if item[1] is None:
            style(ws.cell(r, 1), F_BOLD).value = item[0]
            r += 1
            continue
        key, label, fmt, v, note = item
        ws.cell(r, 1, label).font = F_BODY
        style(ws.cell(r, 6), F_INPUT, fmt).value = v
        style(ws.cell(r, 7), F_NOTE).value = note
        refs[key] = f"Assumptions!$F${r}"
        r += 1
    style(ws.cell(r + 1, 1), F_BODY).value = "Check: plan mix totals 100%"
    style(ws.cell(r + 1, 6), F_BODY, PCT).value = (
        f"={refs['mix_starter']}+{refs['mix_pro']}+{refs['mix_ent']}")
    ws.column_dimensions["A"].width = 62
    for col in "CDEF":
        ws.column_dimensions[col].width = 14
    ws.column_dimensions["G"].width = 80
    return refs


# -------------------------------------------------------------------- Pricing
def build_pricing(wb, A):
    ws = wb.create_sheet("Pricing")
    title(ws, "Pricing vs. subscriber commission",
          "Value-based check: what each tier costs relative to the commission it helps close "
          "and the analyst time it saves.")
    tiers = ["Starter", "Professional", "Enterprise"]
    for i, t in enumerate(tiers):
        style(ws.cell(4, 3 + i), F_BOLD, fill=FILL_HEAD).value = t
    style(ws["A4"], F_BOLD, fill=FILL_HEAD).value = "Per account, per month"
    rows = [
        ("Target subscriber", None, ["Solo broker / advisor", "Brokerage or advisory team",
                                     "Lender, bank, CU, large brokerage"], "text"),
        ("Seats included", NUM, [1, 3, 10], "in"),
        ("Average loan size ($)", USD, [1_500_000, 2_000_000, 3_000_000], "in"),
        ("Fee / commission (% of loan)", '0.00%', [0.01, 0.01, 0.0075], "in"),
        ("Loans closed per month", NUM1, [1.5, 4, 12], "in"),
        ("Expected commission per month ($)", USD, "=C7*C8*C9", "f"),
        ("Deals analyzed per seat per month", NUM1, f"={A['deals_per_seat']}", "link"),
        ("Analyst hours saved per deal analyzed", NUM1, [6, 6, 6], "in"),
        ("Loaded analyst cost per hour ($)", USD, [75, 75, 85], "in"),
        ("Value of time saved per month ($)", USD, "=C6*C11*C12*C13", "f"),
        ("Recommended list price per month ($)", USD, [499, 1499, 4500], "key"),
        ("Price as % of expected commission", PCT, "=IFERROR(C15/C10,0)", "f"),
        ("Customer ROI on time saved alone", MULT, "=IFERROR(C14/C15,0)", "f"),
        ("Value-based ceiling at target share ($)", USD, "=C10*$C$23", "f"),
        ("One-time onboarding fee ($)", USD, [0, 500, 5000], "in"),
        ("Plan mix (from Assumptions)", PCT, None, "mix"),
    ]
    r = 5
    for label, fmt, val, kind in rows:
        ws.cell(r, 1, label).font = F_BODY
        for i in range(3):
            c = ws.cell(r, 3 + i)
            col = get_column_letter(3 + i)
            if kind == "text":
                style(c, F_BODY).value = val[i]
                c.alignment = Alignment(wrap_text=True)
            elif kind in ("in", "key"):
                style(c, F_INPUT, fmt, FILL_KEY if kind == "key" else None).value = val[i]
            elif kind == "link":
                style(c, F_LINK, fmt).value = val
            elif kind == "mix":
                style(c, F_LINK, fmt).value = "=" + A[["mix_starter", "mix_pro", "mix_ent"][i]]
            else:
                style(c, F_BODY, fmt).value = val.replace("C", col).replace("$" + col, "$C")
        r += 1
    # r == 21 now
    style(ws["A23"], F_BODY).value = "Target price as share of commission (value-based ceiling)"
    style(ws["C23"], F_INPUT, PCT, FILL_KEY).value = 0.03
    ws["C23"].comment = Comment("Assumption: B2B tools typically capture 2-5% of the "
                                "revenue they influence. Keep list price below this ceiling.",
                                "model")
    style(ws["A25"], F_BOLD).value = "Blended (by plan mix)"
    blended = [
        ("Blended revenue per account per month (ARPA) ($)", USD, "=SUMPRODUCT(C15:E15,C20:E20)"),
        ("Blended seats per account", NUM1, "=SUMPRODUCT(C6:E6,C20:E20)"),
        ("Blended onboarding fee per new account ($)", USD, "=SUMPRODUCT(C19:E19,C20:E20)"),
    ]
    refs = {}
    for j, (label, fmt, f) in enumerate(blended):
        rr = 26 + j
        ws.cell(rr, 1, label).font = F_BODY
        style(ws.cell(rr, 3), F_BODY, fmt).value = f
        refs[["arpa", "seats", "onboard"][j]] = f"Pricing!$C${rr}"
    style(ws["A30"], F_NOTE).value = (
        "Why flat subscriptions, not a % of commission: taking a share of loan fees can make the "
        "platform look like a broker/finder under some state lending laws (e.g. California "
        "Financing Law) - confirm with regulatory counsel before offering any success-fee plan.")
    ws.column_dimensions["A"].width = 52
    for col in "CDE":
        ws.column_dimensions[col].width = 24
    return refs


# ----------------------------------------------------------------- Unit costs
def build_unit_costs(wb):
    ws = wb.create_sheet("UnitCosts")
    title(ws, "AI and document-processing unit costs",
          "Claude API list prices (USD per million tokens), Anthropic first-party, Oct 2026. "
          "Bedrock pricing may differ.")
    rows = [
        ("Model prices ($ per 1M tokens)", None, None, None),
        ("Claude Opus 5.5 - input", USD2, 4.00, "p_opus_in"),
        ("Claude Opus 5.5 - output", USD2, 20.00, "p_opus_out"),
        ("Claude Opus 5.5 - cache read", USD2, 0.20, "p_opus_cr"),
        ("Claude Sonnet 5.5 - input", USD2, 2.00, "p_son_in"),
        ("Claude Sonnet 5.5 - output", USD2, 10.00, "p_son_out"),
        ("Claude Sonnet 5.5 - cache read", USD2, 0.20, "p_son_cr"),
        ("Claude Haiku 5.5 - input (prompts <=100K)", USD2, 0.10, "p_hai_in"),
        ("Claude Haiku 5.5 - output (prompts <=100K)", USD2, 0.50, "p_hai_out"),
        ("Cache write premium (x input price)", MULT, 1.25, "cache_write_mult"),
        ("Per deal: document extraction (Haiku 5.5)", None, None, None),
        ("Pages per loan package", NUM, 250, "pages"),
        ("Tokens per page", NUM, 1500, "tok_page"),
        ("Structured output tokens per deal", NUM, 40000, "ext_out"),
        ("Extraction cost per deal ($)", USD2,
         "=pages*tok_page/1e6*p_hai_in+ext_out/1e6*p_hai_out", "c_extract"),
        ("Per deal: underwriting analysis, workbook and memo (Opus 5.5)", None, None, None),
        ("Agent turns per deal", NUM, 25, "turns"),
        ("Average context per turn (tokens)", NUM, 120000, "ctx"),
        ("Share of input served from prompt cache", PCT, 0.85, "cache_share"),
        ("Output + thinking tokens per deal", NUM, 80000, "an_out"),
        ("Analysis cost per deal ($)", USD2,
         "=turns*ctx/1e6*(cache_share*p_opus_cr+(1-cache_share)*p_opus_in*cache_write_mult)"
         "+an_out/1e6*p_opus_out", "c_analysis"),
        ("Per deal: OCR for scanned pages (AWS Textract)", None, None, None),
        ("Share of pages needing OCR", PCT, 0.40, "ocr_share"),
        ("OCR price per page ($)", '$0.000', 0.015, "ocr_price"),
        ("OCR cost per deal ($)", USD2, "=pages*ocr_share*ocr_price", "c_ocr"),
        ("Per seat: everyday assistant work (Sonnet 5.5)", None, None, None),
        ("Assistant sessions per seat per month", NUM, 80, "sessions"),
        ("Input tokens per session", NUM, 60000, "s_in"),
        ("Output tokens per session", NUM, 4000, "s_out"),
        ("Assistant cost per seat per month ($)", USD2,
         "=sessions*(s_in/1e6*(cache_share*p_son_cr+(1-cache_share)*p_son_in*cache_write_mult)"
         "+s_out/1e6*p_son_out)", "c_assist"),
        ("Overheads", None, None, None),
        ("Buffer for retries, evals, long documents", PCT, 0.25, "buffer"),
        ("AI cost per deal incl. buffer ($)", USD2, "=(c_extract+c_analysis)*(1+buffer)",
         "llm_deal"),
        ("AI assistant cost per seat incl. buffer ($)", USD2, "=c_assist*(1+buffer)",
         "llm_seat"),
    ]
    names = {}
    r = 4
    for label, fmt, val, key in rows:
        if fmt is None:
            style(ws.cell(r, 1), F_BOLD).value = label
            r += 1
            continue
        ws.cell(r, 1, label).font = F_BODY
        names[key] = f"$C${r}"
        if isinstance(val, str):
            f = val
            for k in sorted(names, key=len, reverse=True):
                f = _replace_name(f, k, names[k])
            style(ws.cell(r, 3), F_BODY, fmt).value = f
        else:
            style(ws.cell(r, 3), F_INPUT, fmt).value = val
        r += 1
    ws.column_dimensions["A"].width = 60
    ws.column_dimensions["C"].width = 16
    return {k: f"UnitCosts!{v}" for k, v in names.items()}


def _replace_name(formula, name, ref):
    import re
    return re.sub(rf"(?<![A-Za-z_$]){re.escape(name)}(?![A-Za-z_0-9])", ref, formula)


# ------------------------------------------------------------- Infrastructure
INFRA = [
    ("ECS Fargate - API (3 x 1 vCPU / 2 GB, ARM)", 90, "Graviton Fargate ~$30/task-month."),
    ("ECS Fargate - workers (4 x 2 vCPU / 4 GB, ARM)", 240, "Autoscale 4-20 tasks."),
    ("RDS PostgreSQL Multi-AZ db.r6g.large + 200 GB gp3", 420, "Encrypted, 35-day PITR."),
    ("NAT gateways (3 AZ) + data processing", 150, "$0.045/hr each + $0.045/GB."),
    ("Interface VPC endpoints (8 services x 3 AZ)", 180, "~$7.30 per endpoint per AZ."),
    ("Application Load Balancer + WAF", 90, "WAF $5/ACL + $1/rule + requests."),
    ("S3 documents + DR replica + audit (Object Lock)", 120, "Grows with tenants."),
    ("KMS platform keys + API requests", 40, "Per-tenant keys are in variable costs."),
    ("CloudTrail data events, GuardDuty, Security Hub, Inspector", 350, "Security monitoring."),
    ("CloudWatch logs and metrics (400-day retention)", 250, ""),
    ("AWS Backup + cross-region RDS backup copies", 120, "DR region us-west-2."),
    ("Staging environment (2 AZ, single-AZ DB)", 600, ""),
    ("AWS Business Support", 300, "Greater of $100 or ~10% of spend."),
]
SAAS = [
    ("Compliance automation (Vanta / Drata)", 1000, "~$12k/yr."),
    ("Observability / SIEM (e.g. Datadog)", 900, ""),
    ("Customer SSO/SCIM (e.g. WorkOS) for enterprise accounts", 500, ""),
    ("Support desk + in-app chat (Intercom / Zendesk)", 400, ""),
    ("Source control, CI/CD, code + dependency scanning", 400, ""),
    ("Endpoint management (MDM) + password manager", 300, "Laptops are in scope for SOC 2."),
    ("E-signature, email, productivity suite", 300, ""),
]


def build_infra(wb):
    ws = wb.create_sheet("Infrastructure")
    title(ws, "Remote servers and operations tooling (monthly, production baseline)",
          "AWS us-east-1 primary, us-west-2 DR. Matches infra/terraform. Estimates at list price.")
    style(ws["A4"], F_BOLD, fill=FILL_HEAD).value = "AWS line item"
    style(ws["C4"], F_BOLD, fill=FILL_HEAD).value = "$ / month"
    style(ws["D4"], F_BOLD, fill=FILL_HEAD).value = "Note"
    r = 5
    for label, v, note in INFRA:
        ws.cell(r, 1, label).font = F_BODY
        style(ws.cell(r, 3), F_INPUT, USD).value = v
        style(ws.cell(r, 4), F_NOTE).value = note
        r += 1
    style(ws.cell(r, 1), F_BOLD).value = "Hosting baseline total"
    style(ws.cell(r, 3), F_BOLD, USD).value = f"=SUM(C5:C{r - 1})"
    infra_ref = f"Infrastructure!$C${r}"
    r += 2
    style(ws.cell(r, 1), F_BOLD, fill=FILL_HEAD).value = "Security and operations SaaS"
    r += 1
    s0 = r
    for label, v, note in SAAS:
        ws.cell(r, 1, label).font = F_BODY
        style(ws.cell(r, 3), F_INPUT, USD).value = v
        style(ws.cell(r, 4), F_NOTE).value = note
        r += 1
    style(ws.cell(r, 1), F_BOLD).value = "SaaS tooling total"
    style(ws.cell(r, 3), F_BOLD, USD).value = f"=SUM(C{s0}:C{r - 1})"
    ws.column_dimensions["A"].width = 60
    ws.column_dimensions["C"].width = 14
    ws.column_dimensions["D"].width = 50
    return infra_ref, f"Infrastructure!$C${r}"


# ------------------------------------------------------------------- Staffing
STAFF = [
    ("Founder / CEO", 12500, 1, "Set to 0 if you will not draw a salary."),
    ("Founding AI / full-stack engineer", 22000, 1, "~$210k x 1.25 burden."),
    ("Full-stack engineer", 18000, 1, ""),
    ("Commercial lending SME / product lead (fractional, then full-time)", 9000, 1,
     "Ex-credit officer; writes policy templates, grades agent output."),
    ("DevSecOps / security engineer", 19000, 4, "Owns SOC 2 controls + infra."),
    ("Account executive (base + commission)", 13000, 7, ""),
    ("Marketing manager", 11000, 10, ""),
    ("Engineer #3", 18000, 13, ""),
    ("Compliance & operations manager", 12000, 16, "Vendor DD questionnaires, audits."),
    ("Account executive #2", 13000, 16, ""),
    ("Engineer #4", 18000, 19, ""),
]


def build_staffing(wb):
    ws = wb.create_sheet("Staffing")
    title(ws, "Team plan (loaded monthly cost = salary x ~1.25 / 12)",
          "Support reps scale with accounts and are in COGS (see Assumptions).")
    for col, h in zip("ACDE", ["Role", "Loaded $ / month", "Start month", "Note"]):
        style(ws[f"{col}4"], F_BOLD, fill=FILL_HEAD).value = h
    r = 5
    for role, cost, start, note in STAFF:
        ws.cell(r, 1, role).font = F_BODY
        style(ws.cell(r, 3), F_INPUT, USD).value = cost
        style(ws.cell(r, 4), F_INPUT, NUM).value = start
        style(ws.cell(r, 5), F_NOTE).value = note
        r += 1
    ws.column_dimensions["A"].width = 64
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["E"].width = 50
    return f"Staffing!$C$5:$C${r - 1}", f"Staffing!$D$5:$D${r - 1}"


# ---------------------------------------------------------------------- Setup
SETUP = [
    ("Entity formation, founder/IP agreements, cap table", 6000, 1),
    ("Regulatory counsel: lending/broker licensing, ECOA/Reg B, UPL, state law memo", 25000, 1),
    ("Terms of service, DPA, privacy policy, AI-use disclosures, MSA template", 12000, 2),
    ("Trademark search and filing", 3000, 2),
    ("Brand, website, product design system", 25000, 2),
    ("Lending template library: credit memo, spreading, policy packs (SME time)", 15000, 3),
    ("Evaluation dataset: synthetic loan packages + expert grading", 15000, 4),
    ("Laptops and equipment (5)", 15000, 1),
    ("SOC 2 readiness consultant", 15000, 4),
    ("SOC 2 Type I audit", 20000, 6),
    ("Independent penetration test before launch", 18000, 6),
    ("Launch marketing: conferences, association sponsorships, collateral", 15000, 6),
]


def build_setup(wb):
    ws = wb.create_sheet("Setup")
    title(ws, "One-time setup costs", "Month = when the cost is paid. Estimates; get quotes.")
    for col, h in zip("ACD", ["Item", "Cost ($)", "Month"]):
        style(ws[f"{col}4"], F_BOLD, fill=FILL_HEAD).value = h
    r = 5
    for item, cost, month in SETUP:
        ws.cell(r, 1, item).font = F_BODY
        style(ws.cell(r, 3), F_INPUT, USD).value = cost
        style(ws.cell(r, 4), F_INPUT, NUM).value = month
        r += 1
    ws.cell(r, 1, "Contingency (% of items above)").font = F_BODY
    style(ws.cell(r, 2), F_INPUT, PCT).value = 0.15
    style(ws.cell(r, 3), F_BODY, USD).value = f"=SUM(C5:C{r - 1})*B{r}"
    style(ws.cell(r, 4), F_INPUT, NUM).value = 1
    r += 1
    style(ws.cell(r, 1), F_BOLD).value = "Total one-time setup"
    style(ws.cell(r, 3), F_BOLD, USD).value = f"=SUM(C5:C{r - 1})"
    ws.column_dimensions["A"].width = 78
    ws.column_dimensions["C"].width = 14
    return f"Setup!$C$5:$C${r - 1}", f"Setup!$D$5:$D${r - 1}", f"Setup!$C${r}"


# -------------------------------------------------------------------- Monthly
def build_monthly(wb, A, P, U, infra_ref, saas_ref, staff, setup):
    ws = wb.create_sheet("Monthly")
    title(ws, "36-month operating model ($)", "All cells are formulas over the input sheets.")
    staff_cost, staff_start = staff
    setup_cost, setup_month, _ = setup
    L = A["launch_month"]

    rows = {}
    spec = [
        ("month", "Month", NUM, lambda c, p: None),
        ("year", "Year", NUM, lambda c, p: f"=ROUNDUP({c}{{month}}/12,0)"),
        ("live", "Live (1 = selling)", NUM, lambda c, p: f"=IF({c}{{month}}>={L},1,0)"),
        None,
        ("beg", "Beginning accounts", NUM1, lambda c, p: "=0" if p is None else f"={p}{{end}}"),
        ("new", "New accounts", NUM1, lambda c, p:
            f"=IF({c}{{live}}=1,MIN({A['new_cap']},{A['new_at_launch']}*(1+{A['new_growth']})"
            f"^({c}{{month}}-{L})),0)"),
        ("churn", "Churned accounts", NUM1, lambda c, p: f"={c}{{beg}}*{A['churn']}"),
        ("end", "Ending accounts", NUM1, lambda c, p: f"={c}{{beg}}+{c}{{new}}-{c}{{churn}}"),
        ("seats", "Seats", NUM1, lambda c, p: f"={c}{{end}}*{P['seats']}"),
        None,
        ("sub_rev", "Subscription revenue", USD, lambda c, p: f"={c}{{end}}*{P['arpa']}"),
        ("onb_rev", "Onboarding fees", USD, lambda c, p: f"={c}{{new}}*{P['onboard']}"),
        ("rev", "Total revenue", USD, lambda c, p: f"={c}{{sub_rev}}+{c}{{onb_rev}}"),
        None,
        ("c_llm", "AI model usage (Claude)", USD, lambda c, p:
            f"={c}{{seats}}*({A['deals_per_seat']}*{U['llm_deal']}+{U['llm_seat']})"),
        ("c_ocr", "Document OCR", USD, lambda c, p:
            f"={c}{{seats}}*{A['deals_per_seat']}*{U['c_ocr']}"),
        ("c_host", "Hosting baseline (servers)", USD, lambda c, p:
            f"=IF({c}{{month}}>={L}-1,{infra_ref},{infra_ref}*{A['build_infra_factor']})"),
        ("c_hostvar", "Hosting variable + tenant keys", USD, lambda c, p:
            f"={c}{{seats}}*{A['infra_var_seat']}+{c}{{end}}*{A['kms_per_account']}"),
        ("c_pay", "Payment processing", USD, lambda c, p: f"={c}{{rev}}*{A['payment_pct']}"),
        ("c_support", "Customer support staff", USD, lambda c, p:
            f"=IF({c}{{live}}=1,MAX(1,ROUNDUP({c}{{end}}/{A['accts_per_csm']},0))"
            f"*{A['csm_cost']},0)"),
        ("cogs", "Total cost of revenue", USD, lambda c, p: f"=SUM({c}{{c_llm}}:{c}{{c_support}})"),
        ("gp", "Gross profit", USD, lambda c, p: f"={c}{{rev}}-{c}{{cogs}}"),
        ("gm", "Gross margin %", PCT, lambda c, p: f"=IFERROR({c}{{gp}}/{c}{{rev}},0)"),
        None,
        ("o_payroll", "Payroll (product, engineering, sales, G&A)", USD, lambda c, p:
            f"=SUMPRODUCT(({staff_start}<={c}{{month}})*{staff_cost})"),
        ("o_mkt", "Sales & marketing (CAC + base)", USD, lambda c, p:
            f"={c}{{new}}*{A['cac']}+IF({c}{{month}}>={L}-2,{A['base_marketing']},0)"),
        ("o_saas", "Security & operations SaaS", USD, lambda c, p: f"={saas_ref}"),
        ("o_ins", "Insurance", USD, lambda c, p: f"={A['insurance']}"),
        ("o_prof", "Professional services", USD, lambda c, p: f"={A['prof_services']}"),
        ("o_comp", "Recurring compliance (SOC 2 Type II, pen tests)", USD, lambda c, p:
            f"=IF({c}{{month}}>={A['compliance_start']},{A['compliance_recurring']},0)"),
        ("o_ga", "Other G&A", USD, lambda c, p: f"={A['ga_other']}"),
        ("o_setup", "One-time setup costs", USD, lambda c, p:
            f"=SUMIF({setup_month},{c}{{month}},{setup_cost})"),
        ("opex", "Total operating expenses", USD, lambda c, p:
            f"=SUM({c}{{o_payroll}}:{c}{{o_setup}})"),
        None,
        ("ebitda", "EBITDA (monthly profit / loss)", USD, lambda c, p: f"={c}{{gp}}-{c}{{opex}}"),
        ("cum", "Cumulative cash flow", USD, lambda c, p:
            f"={c}{{ebitda}}" if p is None else f"={p}{{cum}}+{c}{{ebitda}}"),
        ("totcost", "Total costs (COGS + opex)", USD, lambda c, p: f"={c}{{cogs}}+{c}{{opex}}"),
        None,
        ("h_be", "helper: month if EBITDA-positive", NUM, lambda c, p:
            f"=IF(AND({c}{{live}}=1,{c}{{ebitda}}>0),{c}{{month}},999)"),
        ("h_cum", "helper: month if cumulative cash recovered", NUM, lambda c, p:
            f"=IF(AND({c}{{live}}=1,{c}{{cum}}>=0),{c}{{month}},999)"),
    ]
    r = 4
    for item in spec:
        if item is not None:
            rows[item[0]] = r
        r += 1
    r = 4
    for item in spec:
        if item is None:
            r += 1
            continue
        key, label, fmt, fn = item
        bold = key in ("rev", "gp", "ebitda", "cum", "end", "opex", "cogs")
        style(ws.cell(r, 2), F_BOLD if bold else F_BODY).value = label
        for m in range(1, MONTHS + 1):
            col = get_column_letter(FIRST_COL + m - 1)
            prev = get_column_letter(FIRST_COL + m - 2) if m > 1 else None
            cell = ws.cell(r, FIRST_COL + m - 1)
            if key == "month":
                style(cell, F_BOLD, NUM, FILL_HEAD).value = m
                continue
            f = fn(col, prev).format(**rows)
            style(cell, F_BOLD if bold else F_BODY, fmt).value = f
        r += 1
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 46
    for m in range(MONTHS):
        ws.column_dimensions[get_column_letter(FIRST_COL + m)].width = 11
    ws.freeze_panes = "C5"
    last = get_column_letter(FIRST_COL + MONTHS - 1)
    rng = {k: f"Monthly!$C${v}:${last}${v}" for k, v in rows.items()}
    return rng, rows


# -------------------------------------------------------------------- Summary
def build_summary(wb, A, P, U, R, setup_total, rows):
    ws = wb["Summary"]
    title(ws, "LendAgent - business model summary",
          "Change inputs on Assumptions / Pricing / UnitCosts / Infrastructure / Staffing / Setup.")
    style(ws["A3"], F_BODY).value = "Scenario shown"
    style(ws["C3"], F_LINK).value = "=Assumptions!$G$3"
    items = [
        ("Cost to set up the business", None, None),
        ("One-time setup costs (legal, SOC 2, pen test, brand, equipment)", USD,
         f"={setup_total}", "setup_total"),
        ("Pre-launch burn: all costs before first paid month", USD,
         f"=SUMPRODUCT(({R['month']}<{A['launch_month']})*{R['totcost']})", "prelaunch"),
        ("Peak capital required (deepest point of cumulative cash)", USD,
         f"=MAX(0,-MIN({R['cum']}))", "peak_capital"),
        ("Month of peak capital need", NUM,
         f"=INDEX({R['month']},MATCH(MIN({R['cum']}),{R['cum']},0))", "peak_month"),
        ("Recommended raise (peak need + 25% cushion)", USD, "={peak_capital}*1.25", "raise"),
        ("Monthly run-rate costs", None, None),
        ("Servers / hosting baseline per month (production)", USD,
         "=Infrastructure!$C$18", "infra"),
        ("Security & operations SaaS per month", USD, "=Infrastructure!$C$28", "saas"),
        ("Total costs in month 12", USD, f"=INDEX({R['totcost']},12)", "cost_m12"),
        ("Total costs in month 36", USD, f"=INDEX({R['totcost']},36)", "cost_m36"),
        ("Unit economics (per account per month)", None, None),
        ("Blended price per account (ARPA)", USD, f"={P['arpa']}", "arpa"),
        ("AI + OCR + hosting variable cost per account", USD,
         f"={P['seats']}*({A['deals_per_seat']}*({U['llm_deal']}+{U['c_ocr']})+{U['llm_seat']}"
         f"+{A['infra_var_seat']})+{A['kms_per_account']}", "var_cost"),
        ("Claude AI cost per deal analyzed", USD2, f"={U['llm_deal']}", "llm_deal"),
        ("Contribution after variable costs and card fees", USD,
         f"={{arpa}}*(1-{A['payment_pct']})-{{var_cost}}", "contribution"),
        ("Customer lifetime (months) = 1 / churn", NUM1, f"=1/{A['churn']}", "lifetime"),
        ("Lifetime value (LTV)", USD, "={contribution}*{lifetime}", "ltv"),
        ("Customer acquisition cost (CAC)", USD, f"={A['cac']}", "cac"),
        ("LTV / CAC", MULT, "=IFERROR({ltv}/{cac},0)", "ltv_cac"),
        ("CAC payback (months)", NUM1, "=IFERROR({cac}/{contribution},0)", "payback"),
        ("Milestones", None, None),
        ("First month with positive EBITDA", NUM, f"=MIN({R['h_be']})", "breakeven_month"),
        ("Month cumulative cash turns positive", NUM, f"=MIN({R['h_cum']})", "cash_payback_month"),
        ("Paying accounts - month 12", NUM, f"=INDEX({R['end']},12)", "acc_m12"),
        ("Paying accounts - month 24", NUM, f"=INDEX({R['end']},24)", "acc_m24"),
        ("Paying accounts - month 36", NUM, f"=INDEX({R['end']},36)", "acc_m36"),
        ("Annual recurring revenue (ARR) - month 36", USD,
         f"=INDEX({R['sub_rev']},36)*12", "arr_m36"),
        ("Annual results", None, None),
        ("Revenue - Year 1", USD, f"=SUMIF({R['year']},1,{R['rev']})", "rev_y1"),
        ("Revenue - Year 2", USD, f"=SUMIF({R['year']},2,{R['rev']})", "rev_y2"),
        ("Revenue - Year 3", USD, f"=SUMIF({R['year']},3,{R['rev']})", "rev_y3"),
        ("EBITDA - Year 1", USD, f"=SUMIF({R['year']},1,{R['ebitda']})", "ebitda_y1"),
        ("EBITDA - Year 2", USD, f"=SUMIF({R['year']},2,{R['ebitda']})", "ebitda_y2"),
        ("EBITDA - Year 3", USD, f"=SUMIF({R['year']},3,{R['ebitda']})", "ebitda_y3"),
        ("Gross margin - Year 3", PCT,
         f"=IFERROR(SUMIF({R['year']},3,{R['gp']})/SUMIF({R['year']},3,{R['rev']}),0)", "gm_y3"),
        ("Pricing check", None, None),
        ("Starter price as % of expected commission", PCT, "=Pricing!$C$16", "pct_starter"),
        ("Professional price as % of expected commission", PCT, "=Pricing!$D$16", "pct_pro"),
        ("Enterprise price as % of expected commission", PCT, "=Pricing!$E$16", "pct_ent"),
    ]
    r = 5
    cells = {}
    for it in items:
        if it[1] is None:
            style(ws.cell(r, 1), F_BOLD, fill=FILL_HEAD).value = it[0]
            r += 1
            continue
        label, fmt, f, key = it
        ws.cell(r, 1, label).font = F_BODY
        style(ws.cell(r, 3), F_BODY, fmt).value = f
        cells[key] = f"C{r}"
        r += 1
    # Second pass: resolve {key} references between summary lines.
    for key, ref in cells.items():
        c = ws[ref]
        if "{" in c.value:
            c.value = c.value.format(**cells)
    for key in ("breakeven_month", "cash_payback_month"):
        c = ws[cells[key]]
        c.value = f'=IF({c.value[1:]}=999,"Beyond month 36",{c.value[1:]})'
    for key in ("raise", "peak_capital", "breakeven_month", "arr_m36"):
        ws[cells[key]].fill = FILL_KEY

    ws.column_dimensions["A"].width = 66
    ws.column_dimensions["C"].width = 18

    m = wb["Monthly"]
    chart = LineChart()
    chart.title = "Monthly revenue vs. total costs"
    chart.height, chart.width = 8, 18
    for key in ("rev", "totcost"):
        chart.add_data(Reference(m, min_col=2, max_col=FIRST_COL + MONTHS - 1, min_row=rows[key]),
                       from_rows=True, titles_from_data=True)
    chart.set_categories(Reference(m, min_col=FIRST_COL, max_col=FIRST_COL + MONTHS - 1,
                                   min_row=rows["month"]))
    ws.add_chart(chart, "E5")
    cash = LineChart()
    cash.title = "Cumulative cash flow"
    cash.height, cash.width = 8, 18
    cash.add_data(Reference(m, min_col=2, max_col=FIRST_COL + MONTHS - 1, min_row=rows["cum"]),
                  from_rows=True, titles_from_data=True)
    cash.set_categories(Reference(m, min_col=FIRST_COL, max_col=FIRST_COL + MONTHS - 1,
                                  min_row=rows["month"]))
    ws.add_chart(cash, "E23")
    return cells


def build_readme(wb):
    ws = wb.create_sheet("README", 0)
    title(ws, "How to use this model")
    lines = [
        "1. Pick a scenario in Assumptions!F3 (1 Conservative, 2 Base, 3 Aggressive).",
        "2. Blue cells are inputs; yellow cells are key levers. Black cells are formulas - "
        "don't overwrite them.",
        "3. Summary shows setup cost, capital required, break-even, unit economics, pricing.",
        "4. Pricing compares each plan's price with the commission the subscriber expects to "
        "earn and the analyst time saved.",
        "5. UnitCosts derives Claude AI cost per deal from token volumes and list prices.",
        "6. Infrastructure itemizes the AWS servers defined in infra/terraform.",
        "All figures are planning estimates, not quotes. Validate the starred growth and churn "
        "assumptions with beta customers.",
    ]
    for i, t in enumerate(lines, start=3):
        style(ws.cell(i, 1), F_BODY).value = t
    ws.column_dimensions["A"].width = 120


def build() -> dict:
    wb = Workbook()
    wb.active.title = "Summary"
    A = build_assumptions(wb)
    P = build_pricing(wb, A)
    U = build_unit_costs(wb)
    infra_ref, saas_ref = build_infra(wb)
    assert infra_ref == "Infrastructure!$C$18" and saas_ref == "Infrastructure!$C$28"
    staff = build_staffing(wb)
    setup = build_setup(wb)
    R, rows = build_monthly(wb, A, P, U, infra_ref, saas_ref, staff, setup)
    cells = build_summary(wb, A, P, U, R, setup[2], rows)
    build_readme(wb)
    wb.save(OUT)
    return {"cells": cells, "rows": rows}


# ---------------------------------------------------------------- recalc/run
RECALC = Path("/root/.claude/skills/synced/724d2df6-a7cf-49bb-845a-74a64ab375da_"
              "e19c7505-c904-4c5e-aece-d3a583672567/xlsx/scripts/recalc.py")


def recalc(path: Path) -> dict:
    if RECALC.exists():
        out = subprocess.run([sys.executable, str(RECALC), str(path), "90"],
                             capture_output=True, text=True)
        return json.loads(out.stdout)
    subprocess.run(["soffice", "--headless", "--convert-to", "xlsx", "--outdir",
                    str(path.parent), str(path)], check=True, capture_output=True)
    return {"status": "unverified"}


def run_scenarios(meta: dict) -> dict:
    results = {}
    for n, name in ((1, "Conservative"), (2, "Base"), (3, "Aggressive")):
        tmp = HERE / f".scenario_{n}.xlsx"
        wb = load_workbook(OUT)
        wb["Assumptions"]["F3"] = n
        wb.save(tmp)
        check = recalc(tmp)
        if check.get("status") != "success":
            raise SystemExit(f"Recalculation problem in scenario {name}: {check}")
        vals = load_workbook(tmp, data_only=True)
        s = vals["Summary"]
        res = {k: s[c].value for k, c in meta["cells"].items()}
        m = vals["Monthly"]
        res["series"] = {key: [m.cell(meta["rows"][key], FIRST_COL + i).value
                               for i in range(MONTHS)]
                         for key in ("rev", "totcost", "ebitda", "cum", "end")}
        results[name] = res
        if n == 2:
            shutil.move(tmp, OUT)  # ship the base case with computed values cached
        else:
            tmp.unlink()
    return results


def write_report(results: dict):
    (HERE / "results.json").write_text(json.dumps(results, indent=2, default=float))

    def usd(v):
        return f"${v:,.0f}" if isinstance(v, (int, float)) else str(v)

    rows = [
        ("One-time setup costs", "setup_total", usd),
        ("Pre-launch burn (everything before first paid month)", "prelaunch", usd),
        ("Peak capital required", "peak_capital", usd),
        ("Recommended raise (+25% cushion)", "raise", usd),
        ("Month of peak capital need", "peak_month", lambda v: f"{v:.0f}"),
        ("Servers / hosting per month (production)", "infra", usd),
        ("Security & ops SaaS per month", "saas", usd),
        ("Claude AI cost per deal analyzed", "llm_deal", lambda v: f"${v:,.2f}"),
        ("Blended price per account / month", "arpa", usd),
        ("Variable cost per account / month", "var_cost", usd),
        ("LTV / CAC", "ltv_cac", lambda v: f"{v:.1f}x"),
        ("CAC payback (months)", "payback", lambda v: f"{v:.1f}"),
        ("First EBITDA-positive month", "breakeven_month",
         lambda v: f"{v:.0f}" if isinstance(v, (int, float)) else v),
        ("Cumulative cash turns positive (month)", "cash_payback_month",
         lambda v: f"{v:.0f}" if isinstance(v, (int, float)) else v),
        ("Paying accounts - month 12 / 24 / 36", None, None),
        ("ARR at month 36", "arr_m36", usd),
        ("Revenue Y1 / Y2 / Y3", None, None),
        ("EBITDA Y1 / Y2 / Y3", None, None),
        ("Gross margin Y3", "gm_y3", lambda v: f"{v:.0%}"),
    ]
    names = list(results)
    out = ["# Financial model results", "",
           "Generated by `build_model.py` from `LendAgent_Financial_Model.xlsx` "
           "(recalculated in LibreOffice for each scenario).", "",
           "| Metric | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for label, key, fmt in rows:
        if key is None:
            if label.startswith("Paying"):
                keys = ("acc_m12", "acc_m24", "acc_m36")
                vals = [" / ".join(f"{results[n][k]:,.0f}" for k in keys) for n in names]
            else:
                pre = "rev" if label.startswith("Revenue") else "ebitda"
                vals = [" / ".join(usd(results[n][f"{pre}_y{y}"]) for y in (1, 2, 3))
                        for n in names]
        else:
            vals = [fmt(results[n][key]) for n in names]
        out.append(f"| {label} | " + " | ".join(vals) + " |")
    p = results["Base"]
    out += ["", "## Pricing vs. subscriber commission (base case)", "",
            f"- Starter $499/mo = {p['pct_starter']:.1%} of a solo broker's expected commission",
            f"- Professional $1,499/mo = {p['pct_pro']:.1%} of a team's expected commission",
            f"- Enterprise $4,500/mo = {p['pct_ent']:.1%} of a lender's expected fee income", ""]
    (HERE / "RESULTS.md").write_text("\n".join(out))
    _charts(results)


def _charts(results):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    months = list(range(1, MONTHS + 1))
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    colors = {"Conservative": "#b45f06", "Base": "#1f4e79", "Aggressive": "#38761d"}
    base = results["Base"]["series"]
    axes[0].plot(months, base["rev"], label="Revenue", color="#1f4e79", lw=2)
    axes[0].plot(months, base["totcost"], label="Total costs", color="#999999", lw=2)
    axes[0].set_title("Base case: monthly revenue vs. costs")
    axes[0].legend(frameon=False)
    for name, res in results.items():
        axes[1].plot(months, res["series"]["cum"], label=name, color=colors[name], lw=2)
    axes[1].axhline(0, color="#333333", lw=0.8)
    axes[1].set_title("Cumulative cash flow by scenario")
    axes[1].legend(frameon=False)
    for ax in axes:
        ax.set_xlabel("Month")
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
            lambda v, _: f"${v / 1e6:,.1f}M" if abs(v) >= 1e6 else f"${v / 1e3:,.0f}K"))
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(HERE / "model_charts.png", dpi=150)


if __name__ == "__main__":
    meta = build()
    results = run_scenarios(meta)
    write_report(results)
    print((HERE / "RESULTS.md").read_text())
