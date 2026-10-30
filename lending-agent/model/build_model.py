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
# key, label, format, slow, moderate, faster, source/note
SCENARIO_INPUTS = [
    ("Timing", None),
    ("launch_month", "First paid month (earlier months = build + private beta)", NUM, 9, 8, 7,
     "Slow: one engineer builds the MVP, so launch slips to month 9. See PLAN.md roadmap."),
    ("Customer growth", None),
    ("new_at_launch", "New paying accounts in launch month", NUM1, 2, 4, 6,
     "Founder-led sales from beta waitlist; assumption to validate in beta."),
    ("new_growth", "Monthly growth in new-account adds", PCT, 0.03, 0.05, 0.08,
     "Assumption. Slow = word of mouth and founder selling only."),
    ("new_cap", "Cap on new accounts per month", NUM, 12, 40, 90,
     "How many new brokers the team can onboard in a month."),
    ("churn", "Monthly account churn", PCT, 0.03, 0.03, 0.025,
     "Assumption. SMB vertical SaaS commonly 2-4%/mo."),
    ("Plan mix (share of new accounts)", None),
    ("mix_starter", "Solo Broker plan share", PCT, 0.60, 0.50, 0.45, "Assumption."),
    ("mix_pro", "Broker Team plan share", PCT, 0.32, 0.38, 0.40, "Assumption."),
    ("mix_ent", "Brokerage Firm plan share", PCT, 0.08, 0.12, 0.15,
     "Assumption. Shares must total 100%."),
    ("Usage", None),
    ("deals_per_seat", "Deals analyzed per seat per month", NUM1, 8, 8, 8,
     "Assumption: pipeline deals worked (not closed). Higher usage = higher AI cost."),
    ("Support & acquisition", None),
    ("accts_per_csm", "Accounts per customer-success/support rep", NUM, 50, 55, 60,
     "Assumption for high-touch B2B onboarding."),
    ("cac", "Customer acquisition cost per new account ($)", USD, 2500, 4000, 4000,
     "Assumption: ads, events, referral fees. Slow = mostly founder-led selling, so less "
     "paid spend. Salaries are in Staffing. Validate after launch."),
]

FIXED_INPUTS = [
    ("Costs (all scenarios)", None),
    ("csm_cost", "Customer success rep, loaded monthly cost ($)", USD, 8500,
     "~$80k salary x 1.25 burden / 12."),
    ("base_marketing", "Base marketing spend per month ($), from 2 months pre-launch", USD, 5000,
     "Content, website, broker conferences and associations (e.g. AACFB, state broker groups)."),
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
    ("team_plan", "Team plan: 1 = Full, 2 = Lean, 3 = Very lean, 4 = Side line (see Staffing)",
     NUM, 4,
     "Side line = two partners working from home with no salaries; contract developer "
     "builds and maintains the agent; the broker partner tests and improves it."),
    ("ga_other", "Other G&A per month ($): software seats, travel, co-working", USD, 3000,
     "Estimate."),
    ("Very lean overrides (used when team plan = 3)", None),
    ("vl_base_marketing", "Base marketing per month ($)", USD, 1500,
     "Website, LinkedIn content, one or two broker events a year."),
    ("vl_prof_services", "Accounting and legal retainer per month ($)", USD, 2000, "Estimate."),
    ("vl_ga_other", "Other G&A per month ($)", USD, 1000, "Remote, no office."),
    ("vl_compliance", "Recurring compliance per month ($)", USD, 3500,
     "Smaller-firm SOC 2 Type II + pen test pricing."),
    ("vl_support_threshold", "Founder handles support until accounts exceed", NUM, 25,
     "First support hire after this many paying accounts."),
    ("Side line overrides (used when team plan = 4)", None),
    ("sl_base_marketing", "Base marketing per month ($)", USD, 500,
     "Website and LinkedIn; the broker partner's network does most of the selling."),
    ("sl_cac", "Cost to win each new broker ($)", USD, 1000,
     "Referrals from the partner's network, a free trial, the odd event or ad."),
    ("sl_prof_services", "Bookkeeping, tax and legal per month ($)", USD, 800, "Estimate."),
    ("sl_ga_other", "Other G&A per month ($)", USD, 300, "Software seats; both work from home."),
    ("sl_insurance", "Insurance per month: cyber + tech E&O ($)", USD, 800,
     "Smaller limits to start; raise when brokerage firms sign up."),
    ("sl_compliance", "Annual pen test and security review, per month ($)", USD, 1000,
     "Formal SOC 2 audit deferred until brokerage firms ask for it."),
    ("sl_support_threshold", "Partners handle support until accounts exceed", NUM, 40,
     "First paid support hire after this many paying accounts."),
]


def build_assumptions(wb):
    ws = wb.create_sheet("Assumptions")
    title(ws, "Assumptions",
          "Blue = input you can change. Yellow = scenario selector. Column F feeds the model.")
    style(ws["A3"], F_BOLD).value = "Growth scenario (1 = Slow, 2 = Moderate, 3 = Faster)"
    style(ws["F3"], F_INPUT, NUM, FILL_KEY).value = 1
    style(ws["G3"], F_BODY).value = '=CHOOSE($F$3,"Slow","Moderate","Faster")'
    for col, h in zip("ACDEFG", ["Assumption", "Slow", "Moderate", "Faster",
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
    title(ws, "Pricing and value to the broker",
          "Each plan must deliver at least the target ROI: time saved plus extra commission "
          "from the extra loans the broker can now handle.")
    tiers = ["Solo Broker", "Broker Team", "Brokerage Firm"]
    for i, t in enumerate(tiers):
        style(ws.cell(4, 3 + i), F_BOLD, fill=FILL_HEAD).value = t
    style(ws["A4"], F_BOLD, fill=FILL_HEAD).value = "Per account, per month"
    rows = [
        ("Target subscriber", None, ["Independent commercial loan broker",
                                     "Broker with 2-3 partners or analysts",
                                     "Commercial brokerage firm (up to 10 brokers)"], "text"),
        ("Seats included", NUM, [1, 3, 10], "in"),
        ("Average loan size ($)", USD, [1_500_000, 2_000_000, 2_500_000], "in"),
        ("Broker fee / commission (% of loan)", '0.00%', [0.01, 0.01, 0.01], "in"),
        ("Loans closed per month today", NUM1, [1.5, 4, 8], "in"),
        ("Broker's expected commission per month ($)", USD, "=C7*C8*C9", "f"),
        ("Deals analyzed per seat per month", NUM1, f"={A['deals_per_seat']}", "link"),
        ("Hours saved per deal analyzed", NUM1, [6, 6, 6], "in"),
        ("Value of broker/analyst time per hour ($)", USD, [75, 75, 75], "in"),
        ("Value 1: time saved per month ($)", USD, "=C6*C11*C12*C13", "f"),
        ("Extra loans closed per month with the freed-up time", '0.00', [0.25, 0.5, 1.0], "in"),
        ("Value 2: extra commission per month ($)", USD, "=C15*C7*C8", "f"),
        ("Total value to the broker per month ($)", USD, "=C14+C16", "f"),
        ("Monthly price ($)", USD, [999, 2499, 6999], "key"),
        ("Broker ROI (value / price)", MULT, "=IFERROR(C17/C18,0)", "f"),
        ("Price as % of value delivered", PCT, "=IFERROR(C18/C17,0)", "f"),
        ("Price as % of broker's commission", PCT, "=IFERROR(C18/C10,0)", "f"),
        ("Value check", None, '=IF(C19>=$C$27,"OK","Price too high for value")', "f"),
        ("One-time onboarding fee ($)", USD, [0, 500, 2500], "in"),
        ("Plan mix (from Assumptions)", PCT, None, "mix"),
    ]
    r = 5
    for label, fmt, val, kind in rows:
        ws.cell(r, 1, label).font = F_BOLD if label.startswith(("Total value", "Monthly price",
                                                                  "Broker ROI")) else F_BODY
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
    # r == 25 now
    style(ws["A27"], F_BODY).value = "Minimum broker ROI for a plan to pass the value check"
    style(ws["C27"], F_INPUT, MULT, FILL_KEY).value = 5
    ws["C27"].comment = Comment("Assumption: B2B software usually needs to return 5-10x its "
                                "price to sell easily and keep customers.", "model")
    style(ws["A29"], F_BOLD).value = "Blended (by plan mix)"
    blended = [
        ("Blended monthly fee per account (ARPA) ($)", USD, "=SUMPRODUCT(C18:E18,C24:E24)"),
        ("Blended seats per account", NUM1, "=SUMPRODUCT(C6:E6,C24:E24)"),
        ("Blended onboarding fee per new account ($)", USD, "=SUMPRODUCT(C23:E23,C24:E24)"),
    ]
    refs = {}
    for j, (label, fmt, f) in enumerate(blended):
        rr = 30 + j
        ws.cell(rr, 1, label).font = F_BODY
        style(ws.cell(rr, 3), F_BODY, fmt).value = f
        refs[["arpa", "seats", "onboard"][j]] = f"Pricing!$C${rr}"
    style(ws["A34"], F_NOTE).value = (
        "Flat monthly pricing only: we take no share of broker commissions. Proving the value: "
        "the app reports each broker's hours saved and deals worked every month (see PLAN.md).")
    ws.column_dimensions["A"].width = 56
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
    # item, production $/mo, side-line $/mo (smaller footprint), note
    ("ECS Fargate - API (3 x 1 vCPU / 2 GB, ARM)", 90, 30, "Side line: 1 task."),
    ("ECS Fargate - workers (4 x 2 vCPU / 4 GB, ARM)", 240, 60, "Side line: 1-2 tasks."),
    ("RDS PostgreSQL Multi-AZ db.r6g.large + 200 GB gp3", 420, 140,
     "Side line: db.t4g.medium Multi-AZ. Encrypted, 35-day PITR."),
    ("NAT gateways (3 AZ) + data processing", 150, 75, "Side line: 2 AZ."),
    ("Interface VPC endpoints (8 services x 3 AZ)", 180, 120, "~$7.30 per endpoint per AZ."),
    ("Application Load Balancer + WAF", 90, 45, "WAF $5/ACL + $1/rule + requests."),
    ("S3 documents + DR replica + audit (Object Lock)", 120, 30, "Grows with tenants."),
    ("KMS platform keys + API requests", 40, 20, "Per-tenant keys are in variable costs."),
    ("CloudTrail data events, GuardDuty, Security Hub, Inspector", 350, 100,
     "Security monitoring."),
    ("CloudWatch logs and metrics (400-day retention)", 250, 60, ""),
    ("AWS Backup + cross-region RDS backup copies", 120, 40, "DR region us-west-2."),
    ("Staging environment (2 AZ, single-AZ DB)", 600, 100,
     "Side line: started only when testing."),
    ("AWS support plan", 300, 29, "Side line: Developer plan."),
]
SAAS = [
    # item, full/lean $ per month, very lean $ per month, note
    ("Compliance automation (Vanta / Drata)", 1000, 700, "~$12k/yr; startup pricing lower."),
    ("Observability / SIEM (e.g. Datadog)", 900, 200, "Very lean: CloudWatch + free tiers."),
    ("Single sign-on (e.g. WorkOS) for brokerage-firm accounts", 500, 0, "Add when firms sign."),
    ("Support desk + in-app chat (Intercom / Zendesk)", 400, 100, ""),
    ("Source control, CI/CD, code + dependency scanning", 400, 100, ""),
    ("Endpoint management (MDM) + password manager", 300, 100, "Laptops are in scope for SOC 2."),
    ("E-signature, email, productivity suite", 300, 100, ""),
]
SAAS_SIDE_LINE = [300, 100, 0, 50, 50, 50, 50]  # same order as SAAS


def build_infra(wb, A):
    ws = wb.create_sheet("Infrastructure")
    title(ws, "Remote servers and operations tooling (monthly, production baseline)",
          "AWS us-east-1 primary, us-west-2 DR. Matches infra/terraform. Estimates at list price.")
    style(ws["A4"], F_BOLD, fill=FILL_HEAD).value = "AWS line item"
    style(ws["C4"], F_BOLD, fill=FILL_HEAD).value = "$ / month"
    style(ws["D4"], F_BOLD, fill=FILL_HEAD).value = "Note"
    style(ws["F4"], F_BOLD, fill=FILL_HEAD).value = "Side line $ / month"
    r = 5
    for label, v, sl, note in INFRA:
        ws.cell(r, 1, label).font = F_BODY
        style(ws.cell(r, 3), F_INPUT, USD).value = v
        style(ws.cell(r, 6), F_INPUT, USD).value = sl
        style(ws.cell(r, 4), F_NOTE).value = note
        r += 1
    style(ws.cell(r, 1), F_BOLD).value = "Hosting baseline total"
    style(ws.cell(r, 3), F_BOLD, USD).value = f"=SUM(C5:C{r - 1})"
    style(ws.cell(r, 6), F_BOLD, USD).value = f"=SUM(F5:F{r - 1})"
    infra_ref = (f"IF({A['team_plan']}=4,Infrastructure!$F${r},Infrastructure!$C${r})")
    r += 2
    style(ws.cell(r, 1), F_BOLD, fill=FILL_HEAD).value = "Security and operations SaaS"
    style(ws.cell(r, 3), F_BOLD, fill=FILL_HEAD).value = "Full / lean"
    style(ws.cell(r, 5), F_BOLD, fill=FILL_HEAD).value = "Very lean"
    style(ws.cell(r, 6), F_BOLD, fill=FILL_HEAD).value = "Side line"
    r += 1
    s0 = r
    for (label, v, vl, note), sl in zip(SAAS, SAAS_SIDE_LINE):
        ws.cell(r, 1, label).font = F_BODY
        style(ws.cell(r, 3), F_INPUT, USD).value = v
        style(ws.cell(r, 4), F_NOTE).value = note
        style(ws.cell(r, 5), F_INPUT, USD).value = vl
        style(ws.cell(r, 6), F_INPUT, USD).value = sl
        r += 1
    style(ws.cell(r, 1), F_BOLD).value = "SaaS tooling total"
    style(ws.cell(r, 3), F_BOLD, USD).value = f"=SUM(C{s0}:C{r - 1})"
    style(ws.cell(r, 5), F_BOLD, USD).value = f"=SUM(E{s0}:E{r - 1})"
    style(ws.cell(r, 6), F_BOLD, USD).value = f"=SUM(F{s0}:F{r - 1})"
    ws.column_dimensions["A"].width = 60
    ws.column_dimensions["C"].width = 14
    ws.column_dimensions["D"].width = 40
    ws.column_dimensions["E"].width = 14
    ws.column_dimensions["F"].width = 18
    t = A["team_plan"]
    return infra_ref, (f"CHOOSE({t},Infrastructure!$C${r},Infrastructure!$C${r},"
                       f"Infrastructure!$E${r},Infrastructure!$F${r})")


# ------------------------------------------------------------------- Staffing
STAFF = [
    # role, full cost/start, lean cost/start, very lean cost/start (99 = not hired in 36 months)
    ("Founder / CEO", 12500, 1, 12500, 13, 12500, 25,
     "Lean: unpaid for 12 months. Very lean: unpaid for 24 months; also sells and supports."),
    ("Founding AI / full-stack engineer", 22000, 1, 22000, 1, 22000, 1,
     "~$210k x 1.25 burden. Very lean: the only engineer until month 19."),
    ("Full-stack engineer", 18000, 1, 18000, 7, 18000, 19, ""),
    ("Commercial lending SME / product lead", 9000, 1, 4500, 1, 3000, 1,
     "Ex-broker or credit officer; builds package templates, grades agent output. "
     "Lean: half-time. Very lean: about one day a week."),
    ("DevSecOps / security engineer", 19000, 4, 6000, 3, 3000, 3,
     "Owns SOC 2 controls + infra. Lean/very lean: fractional contractor."),
    ("Account executive (base + commission)", 13000, 7, 13000, 10, 13000, 99,
     "Very lean: founder sells."),
    ("Marketing manager", 11000, 10, 11000, 19, 11000, 99, ""),
    ("Engineer #3", 18000, 13, 18000, 16, 18000, 99, ""),
    ("Compliance & operations manager", 12000, 16, 12000, 25, 12000, 99,
     "Security questionnaires, audits."),
    ("Account executive #2", 13000, 16, 13000, 22, 13000, 99, ""),
    ("Engineer #4", 18000, 19, 18000, 28, 18000, 99, ""),
    ("Contract developer, part-time (maintenance and improvements)", 0, 99, 0, 99, 0, 99,
     "Side line only: after the MVP is delivered (MVP build is in Setup)."),
]

# Side line: two unpaid partners, so only contractors are paid. Same row order as STAFF.
SIDE_LINE = [(0, 99), (0, 99), (0, 99), (0, 99), (1500, 3), (0, 99), (0, 99), (0, 99),
             (0, 99), (0, 99), (0, 99), (4000, 7)]


def build_staffing(wb):
    ws = wb.create_sheet("Staffing")
    title(ws, "Team plans (loaded monthly cost = salary x ~1.25 / 12)",
          "Pick the plan in Assumptions. Start month 99 = not hired within 36 months.")
    heads = ["Role", "Full: $/mo", "Full: start", "Lean: $/mo", "Lean: start",
             "Very lean: $/mo", "Very lean: start", "Side line: $/mo", "Side line: start",
             "Note"]
    for col, h in zip("ACDEFGHIJK", heads):
        style(ws[f"{col}4"], F_BOLD, fill=FILL_HEAD).value = h
    assert len(SIDE_LINE) == len(STAFF)
    r = 5
    for (role, *vals, note), sl in zip(STAFF, SIDE_LINE):
        ws.cell(r, 1, role).font = F_BODY
        for j, v in enumerate(list(vals) + list(sl)):
            style(ws.cell(r, 3 + j), F_INPUT, USD if j % 2 == 0 else NUM).value = v
        style(ws.cell(r, 11), F_NOTE).value = note
        r += 1
    ws.column_dimensions["A"].width = 52
    for col in "CDEFGHIJ":
        ws.column_dimensions[col].width = 14
    ws.column_dimensions["K"].width = 80
    last = r - 1
    return tuple(f"Staffing!${c}$5:${c}${last}" for c in "CDEFGHIJ")


# ---------------------------------------------------------------------- Setup
SETUP = [
    # item, full/lean cost, very lean cost, side-line cost, month
    ("Entity formation, founder/IP agreements, cap table", 6000, 3000, 2500, 1),
    ("Legal review: broker agreement, disclaimers, ECOA/Reg B and UPL guardrails",
     25000, 10000, 6000, 1),
    ("Terms of service, DPA, privacy policy, AI-use disclosures, MSA template",
     12000, 8000, 4000, 2),
    ("Trademark search and filing", 3000, 1500, 0, 2),
    ("Brand, website, product design system", 25000, 6000, 2000, 2),
    ("Lending template library: package, spreading, broker profiles (SME time)",
     15000, 5000, 0, 3),
    ("Evaluation dataset: synthetic loan packages + expert grading", 15000, 5000, 1500, 4),
    ("Laptops and equipment", 15000, 6000, 0, 1),
    ("SOC 2 readiness consultant", 15000, 0, 0, 4),
    ("SOC 2 Type I audit (side line: deferred until firms require it)", 20000, 15000, 0, 6),
    ("Independent penetration test before launch", 18000, 10000, 6000, 6),
    ("Launch marketing: conferences, association sponsorships, collateral", 15000, 3000, 1000, 6),
    ("Contract developer: MVP milestone 1 (document intake + extraction)", 0, 0, 20000, 2),
    ("Contract developer: MVP milestone 2 (analysis, workbook, loan package)", 0, 0, 20000, 4),
    ("Contract developer: MVP milestone 3 (security hardening, billing, launch)", 0, 0, 20000, 6),
]


def build_setup(wb, A):
    ws = wb.create_sheet("Setup")
    title(ws, "One-time setup costs", "Month = when the cost is paid. Estimates; get quotes.")
    for col, h in zip("ACDEF", ["Item", "Full / lean ($)", "Month", "Very lean ($)",
                                "Side line ($)"]):
        style(ws[f"{col}4"], F_BOLD, fill=FILL_HEAD).value = h
    r = 5
    for item, cost, vl, sl, month in SETUP:
        ws.cell(r, 1, item).font = F_BODY
        style(ws.cell(r, 3), F_INPUT, USD).value = cost
        style(ws.cell(r, 4), F_INPUT, NUM).value = month
        style(ws.cell(r, 5), F_INPUT, USD).value = vl
        style(ws.cell(r, 6), F_INPUT, USD).value = sl
        r += 1
    ws.cell(r, 1, "Contingency (% of items above)").font = F_BODY
    style(ws.cell(r, 2), F_INPUT, PCT).value = 0.15
    style(ws.cell(r, 3), F_BODY, USD).value = f"=SUM(C5:C{r - 1})*B{r}"
    style(ws.cell(r, 4), F_INPUT, NUM).value = 1
    style(ws.cell(r, 5), F_BODY, USD).value = f"=SUM(E5:E{r - 1})*B{r}"
    style(ws.cell(r, 6), F_BODY, USD).value = f"=SUM(F5:F{r - 1})*B{r}"
    r += 1
    style(ws.cell(r, 1), F_BOLD).value = "Total one-time setup"
    style(ws.cell(r, 3), F_BOLD, USD).value = f"=SUM(C5:C{r - 1})"
    style(ws.cell(r, 5), F_BOLD, USD).value = f"=SUM(E5:E{r - 1})"
    style(ws.cell(r, 6), F_BOLD, USD).value = f"=SUM(F5:F{r - 1})"
    ws.column_dimensions["A"].width = 84
    for col in "CDEF":
        ws.column_dimensions[col].width = 14
    t = A["team_plan"]
    months = f"Setup!$D$5:$D${r - 1}"
    full = f"SUMIF({months},{{m}},Setup!$C$5:$C${r - 1})"
    monthly = (f"CHOOSE({t},{full},{full},SUMIF({months},{{m}},Setup!$E$5:$E${r - 1}),"
               f"SUMIF({months},{{m}},Setup!$F$5:$F${r - 1}))")
    total = f"CHOOSE({t},Setup!$C${r},Setup!$C${r},Setup!$E${r},Setup!$F${r})"
    return monthly, total


# -------------------------------------------------------------------- Monthly
def build_monthly(wb, A, P, U, infra_ref, saas_ref, staff, setup):
    ws = wb.create_sheet("Monthly")
    title(ws, "36-month operating model ($)", "All cells are formulas over the input sheets.")
    staff_cost, staff_start, lean_cost, lean_start, vl_cost, vl_start, sl_cost, sl_start = staff
    setup_monthly = setup[0]
    L = A["launch_month"]
    T = A["team_plan"]
    last_col = get_column_letter(FIRST_COL + MONTHS - 1)

    def plan(key, full=None):  # value by team plan: full, lean, very lean, side line
        base = full if full is not None else A[key]
        vlean = A.get("vl_" + key, base)
        return f"CHOOSE({T},{base},{base},{vlean},{A['sl_' + key]})"


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
            f"=IF({c}{{live}}=1,IF({c}{{end}}<={plan('support_threshold', '0')},0,"
            f"MAX(1,ROUNDUP({c}{{end}}/{A['accts_per_csm']},0))*{A['csm_cost']}),0)"),
        ("cogs", "Total cost of revenue", USD, lambda c, p: f"=SUM({c}{{c_llm}}:{c}{{c_support}})"),
        ("gp", "Gross profit", USD, lambda c, p: f"={c}{{rev}}-{c}{{cogs}}"),
        ("gm", "Gross margin %", PCT, lambda c, p: f"=IFERROR({c}{{gp}}/{c}{{rev}},0)"),
        None,
        ("o_payroll", "Payroll (product, engineering, sales, G&A)", USD, lambda c, p:
            f"=CHOOSE({A['team_plan']},SUMPRODUCT(({staff_start}<={c}{{month}})*{staff_cost}),"
            f"SUMPRODUCT(({lean_start}<={c}{{month}})*{lean_cost}),"
            f"SUMPRODUCT(({vl_start}<={c}{{month}})*{vl_cost}),"
            f"SUMPRODUCT(({sl_start}<={c}{{month}})*{sl_cost}))"),
        ("o_mkt", "Sales & marketing (CAC + base)", USD, lambda c, p:
            f"={c}{{new}}*{plan('cac')}+IF({c}{{month}}>={L}-2,{plan('base_marketing')},0)"),
        ("o_saas", "Security & operations SaaS", USD, lambda c, p: f"={saas_ref}"),
        ("o_ins", "Insurance", USD, lambda c, p: f"={plan('insurance')}"),
        ("o_prof", "Professional services", USD, lambda c, p: f"={plan('prof_services')}"),
        ("o_comp", "Recurring compliance (SOC 2 Type II, pen tests)", USD, lambda c, p:
            f"=IF({c}{{month}}>={A['compliance_start']},"
            f"{plan('compliance', A['compliance_recurring'])},0)"),
        ("o_ga", "Other G&A", USD, lambda c, p: f"={plan('ga_other')}"),
        ("o_setup", "One-time setup costs", USD, lambda c, p:
            "=" + setup_monthly.replace("{m}", c + "{month}")),
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
def build_summary(wb, A, P, U, R, setup_total, infra_ref, saas_ref, rows):
    ws = wb["Summary"]
    title(ws, "LendAgent - business model summary",
          "Change inputs on Assumptions / Pricing / UnitCosts / Infrastructure / Staffing / Setup.")
    style(ws["A3"], F_BODY).value = "Scenario shown"
    style(ws["C3"], F_LINK).value = "=Assumptions!$G$3"
    style(ws["D3"], F_BODY).value = ('=CHOOSE(' + A["team_plan"] +
                                     ',"Full team","Lean team","Very lean team","Side line")')
    items = [
        ("Cost to set up the business", None, None),
        ("One-time setup costs (legal, SOC 2, pen test, brand, equipment)", USD,
         f"={setup_total}", "setup_total"),
        ("Pre-launch burn: all costs before first paid month", USD,
         f"=SUMPRODUCT(({R['month']}<{A['launch_month']})*{R['totcost']})", "prelaunch"),
        ("Peak operating capital needed (salaries, servers, marketing until profitable; no loan funding)", USD,
         f"=MAX(0,-MIN({R['cum']}))", "peak_capital"),
        ("Month of peak capital need", NUM,
         f"=INDEX({R['month']},MATCH(MIN({R['cum']}),{R['cum']},0))", "peak_month"),
        ("Recommended funding for the business (peak need + 25% cushion)", USD, "={peak_capital}*1.25", "raise"),
        ("Monthly run-rate costs", None, None),
        ("Servers / hosting baseline per month (production)", USD,
         "=" + infra_ref, "infra"),
        ("Security & operations SaaS per month", USD, "=" + saas_ref, "saas"),
        ("Total costs in month 12", USD, f"=INDEX({R['totcost']},12)", "cost_m12"),
        ("Total costs in month 36", USD, f"=INDEX({R['totcost']},36)", "cost_m36"),
        ("Unit economics (per account per month)", None, None),
        ("Blended monthly fee per account", USD, f"={P['arpa']}", "arpa"),
        ("AI + OCR + hosting variable cost per account", USD,
         f"={P['seats']}*({A['deals_per_seat']}*({U['llm_deal']}+{U['c_ocr']})+{U['llm_seat']}"
         f"+{A['infra_var_seat']})+{A['kms_per_account']}", "var_cost"),
        ("Claude AI cost per deal analyzed", USD2, f"={U['llm_deal']}", "llm_deal"),
        ("Contribution after variable costs and card fees", USD,
         f"={{arpa}}*(1-{A['payment_pct']})-{{var_cost}}", "contribution"),
        ("Customer lifetime (months) = 1 / churn", NUM1, f"=1/{A['churn']}", "lifetime"),
        ("Lifetime value (LTV)", USD, "={contribution}*{lifetime}", "ltv"),
        ("Customer acquisition cost (CAC)", USD,
         f"=CHOOSE({A['team_plan']},{A['cac']},{A['cac']},{A['cac']},{A['sl_cac']})", "cac"),
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
        ("Solo Broker: broker ROI (value / price)", MULT, "=Pricing!$C$19", "roi_starter"),
        ("Broker Team: broker ROI (value / price)", MULT, "=Pricing!$D$19", "roi_pro"),
        ("Brokerage Firm: broker ROI (value / price)", MULT, "=Pricing!$E$19", "roi_ent"),
        ("Solo Broker: price as % of commission", PCT, "=Pricing!$C$21", "pct_starter"),
        ("Broker Team: price as % of commission", PCT, "=Pricing!$D$21", "pct_pro"),
        ("Brokerage Firm: price as % of commission", PCT, "=Pricing!$E$21", "pct_ent"),
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
        "1. Pick a growth scenario in Assumptions!F3 (1 Slow, 2 Moderate, 3 Faster) and a team "
        "plan in the team_plan row (1 Full, 2 Lean, 3 Very lean). Shipped as Slow + Very lean.",
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
    infra_ref, saas_ref = build_infra(wb, A)
    staff = build_staffing(wb)
    setup = build_setup(wb, A)
    R, rows = build_monthly(wb, A, P, U, infra_ref, saas_ref, staff, setup)
    cells = build_summary(wb, A, P, U, R, setup[1], infra_ref, saas_ref, rows)
    build_readme(wb)
    wb.save(OUT)
    def cell(ref):
        return ref.split("!")[1].replace("$", "")
    return {"cells": cells, "rows": rows, "team_cell": cell(A["team_plan"])}


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


# (label, growth scenario, team plan, price override for the three plans)
RUNS = (
    ("Side line, slow growth (your plan)", 1, 4, None),
    ("Side line, moderate growth", 2, 4, None),
    ("Side line, slow growth, at $499 / $1,499 / $3,999", 1, 4, (499, 1499, 3999)),
    ("Very lean team (paid founder + engineer), slow growth", 1, 3, None),
)


def run_scenarios(meta: dict) -> dict:
    results = {}
    for i, (label, scen, team, prices) in enumerate(RUNS):
        tmp = HERE / f".scenario_{i}.xlsx"
        wb = load_workbook(OUT)
        ws = wb["Assumptions"]
        ws["F3"], ws[meta["team_cell"]] = scen, team
        if prices:
            for col, price in zip("CDE", prices):
                wb["Pricing"][f"{col}18"] = price
        wb.save(tmp)
        check = recalc(tmp)
        if check.get("status") != "success":
            raise SystemExit(f"Recalculation problem in {label}: {check}")
        vals = load_workbook(tmp, data_only=True)
        s = vals["Summary"]
        res = {k: s[c].value for k, c in meta["cells"].items()}
        m = vals["Monthly"]
        res["series"] = {key: [m.cell(meta["rows"][key], FIRST_COL + j).value
                               for j in range(MONTHS)]
                         for key in ("rev", "totcost", "ebitda", "cum", "end")}
        results[label] = res
        if i == 0:
            final = tmp  # ship the user's plan with computed values cached
        else:
            tmp.unlink()
    shutil.move(final, OUT)
    return results


def _table(results: dict) -> list[str]:
    def usd(v):
        return f"${v:,.0f}" if isinstance(v, (int, float)) else str(v)

    def month(v):
        return f"{v:.0f}" if isinstance(v, (int, float)) else v

    rows = [
        ("One-time setup costs", "setup_total", usd),
        ("Spend before the first paying broker", "prelaunch", usd),
        ("Peak operating capital needed (no loan funding)", "peak_capital", usd),
        ("Recommended funding (+25% cushion)", "raise", usd),
        ("Month of peak capital need", "peak_month", month),
        ("Servers / hosting per month (production)", "infra", usd),
        ("Security & ops software per month", "saas", usd),
        ("Claude AI cost per deal analyzed", "llm_deal", lambda v: f"${v:,.2f}"),
        ("Blended monthly fee per broker account", "arpa", usd),
        ("Variable cost per account / month", "var_cost", usd),
        ("LTV / CAC", "ltv_cac", lambda v: f"{v:.1f}x"),
        ("First month with a monthly profit (EBITDA)", "breakeven_month", month),
        ("Month all money spent is earned back", "cash_payback_month", month),
        ("Paying broker accounts - month 12 / 24 / 36", None, None),
        ("Annual revenue run-rate at month 36", "arr_m36", usd),
        ("Revenue Y1 / Y2 / Y3", None, None),
        ("EBITDA Y1 / Y2 / Y3", None, None),
        ("Gross margin Y3", "gm_y3", lambda v: f"{v:.0%}"),
    ]
    names = list(results)
    out = ["| Metric | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
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
    return out


def write_report(results: dict):
    (HERE / "results.json").write_text(json.dumps(results, indent=2, default=float))
    p = results[RUNS[0][0]]
    out = ["# Financial model results", "",
           "Generated by `build_model.py` from `LendAgent_Financial_Model.xlsx`, recalculated in "
           "LibreOffice for each case. Pricing is **flat monthly fees** ($999 / $2,499 / $6,999) "
           "with no share of broker commission, unless noted.", "",
           "**Side line** = two partners working from home with no salaries. A contract "
           "developer builds the MVP ($60k in three milestones) and then maintains it part-time "
           "($4k/mo). The broker partner tests and improves the agent and brings in the first "
           "brokers. A part-time security contractor costs $1.5k/mo. The formal SOC 2 audit is "
           "deferred until brokerage firms ask for it.", "",
           "Capital figures are **operating money for the software business** (salaries, "
           "servers, AI usage, marketing) until revenue covers costs. The business never lends "
           "or funds loans.", ""] + _table(results) + [
           "", "## Value to the broker (does each plan pay for itself?)", "",
           f"- Solo Broker $999/mo: returns {p['roi_starter']:.1f}x its price "
           f"({p['pct_starter']:.1%} of the broker's commission)",
           f"- Broker Team $2,499/mo: returns {p['roi_pro']:.1f}x its price "
           f"({p['pct_pro']:.1%} of commission)",
           f"- Brokerage Firm $6,999/mo: returns {p['roi_ent']:.1f}x its price "
           f"({p['pct_ent']:.1%} of commission)", "",
           "Value = hours saved (6 per deal at $75/hr) + commission on the extra loans the "
           "broker can close with that time (0.25 / 0.5 / 1 extra loan a month). The target is "
           "at least 5x. See the Pricing sheet.", ""]
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
    main = results[RUNS[0][0]]["series"]
    axes[0].fill_between(months, main["rev"], color="#1f4e79", alpha=0.85,
                         label="Revenue (monthly fees)")
    axes[0].plot(months, main["totcost"], label="Total costs", color="#333333", lw=2)
    axes[0].set_title("Your plan (side line, slow growth): revenue vs. costs")
    axes[0].legend(frameon=False, loc="upper left")
    colors = ["#1f4e79", "#999999", "#b45f06", "#38761d"]
    styles = ["-", "--", "-", "-"]
    for (name, res), col, ls in zip(results.items(), colors, styles):
        axes[1].plot(months, res["series"]["cum"], label=name, color=col, lw=2, ls=ls)
    axes[1].axhline(0, color="#333333", lw=0.8)
    axes[1].set_title("Cumulative cash flow")
    axes[1].legend(frameon=False, fontsize=8)
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
