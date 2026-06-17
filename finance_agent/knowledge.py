"""Knowledge bank: capital-gains taxation reference and reduction strategies.

This is curated reference content the agent can retrieve to advise on lowering
capital-gains taxes. Figures reflect the 2025 U.S. federal tax year. Each entry
is concise and points to the relevant Internal Revenue Code (IRC) section. None
of this is a substitute for a CPA/tax attorney — strategies have eligibility
rules and risks that must be checked for the individual's situation.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Reference facts (2025)
# --------------------------------------------------------------------------- #
CAPITAL_GAINS_FACTS = {
    "tax_year": 2025,
    "holding_period": "Assets held 1 year or less = SHORT-TERM, taxed at ordinary "
                      "income rates (up to 37%). Held MORE than 1 year = LONG-TERM, "
                      "taxed at preferential 0% / 15% / 20% rates.",
    "long_term_rate_breakpoints_taxable_income": {
        "single": {"0%_up_to": 48350, "15%_up_to": 533400, "20%_above": 533400},
        "married_joint": {"0%_up_to": 96700, "15%_up_to": 600050, "20%_above": 600050},
        "married_separate": {"0%_up_to": 48350, "15%_up_to": 300000, "20%_above": 300000},
        "head_of_household": {"0%_up_to": 64750, "15%_up_to": 566700, "20%_above": 566700},
    },
    "niit": "Net Investment Income Tax: extra 3.8% on the lesser of net investment "
            "income or MAGI over a statutory threshold ($200k single/HoH, $250k "
            "married joint, $125k married separate). Thresholds are NOT indexed to "
            "inflation.",
    "special_rates": {
        "collectibles": "Long-term gains on collectibles (art, coins, metals) are "
                        "taxed at a maximum 28% rate.",
        "unrecaptured_1250": "Unrecaptured §1250 gain from depreciation on real "
                             "property is taxed at a maximum 25% rate.",
        "qualified_dividends": "Qualified dividends use the same 0/15/20% rates as "
                               "long-term gains.",
    },
    "capital_losses": "Capital losses offset capital gains dollar-for-dollar. Net "
                      "losses up to $3,000/year ($1,500 if married separate) offset "
                      "ordinary income; the remainder carries forward indefinitely.",
}

# --------------------------------------------------------------------------- #
# Reduction / deferral strategies
# --------------------------------------------------------------------------- #
# Each strategy: id, name, summary, how_it_works, best_for, caveats, irc.
STRATEGIES = [
    {
        "id": "hold_long_term",
        "name": "Hold for more than one year",
        "tags": ["timing", "holding period", "basic", "rate"],
        "summary": "Convert short-term gains (ordinary rates up to 37%) into "
                   "long-term gains (0/15/20%) by holding > 1 year.",
        "how_it_works": "The holding period starts the day after purchase. Crossing "
                        "the 1-year mark can cut the rate by 10-20+ points.",
        "best_for": "Anyone sitting on an appreciated asset close to the one-year mark.",
        "caveats": "Don't let the tax tail wag the investment dog — market risk over "
                   "the extra holding period may outweigh the tax saving.",
        "irc": "IRC §1222",
    },
    {
        "id": "tax_loss_harvesting",
        "name": "Tax-loss harvesting",
        "tags": ["losses", "offset", "timing", "niit"],
        "summary": "Sell losing positions to realize losses that offset realized "
                   "gains (and up to $3,000 of ordinary income).",
        "how_it_works": "Net losses against gains dollar-for-dollar; excess up to "
                        "$3,000/yr offsets ordinary income; the rest carries forward.",
        "best_for": "Years with large realized gains, or anyone with depreciated "
                    "holdings in a taxable account.",
        "caveats": "WASH-SALE RULE: you cannot deduct the loss if you buy the same "
                   "or a substantially identical security within 30 days before or "
                   "after the sale. Use a similar (not identical) replacement.",
        "irc": "IRC §1211, §1091 (wash sale)",
    },
    {
        "id": "zero_bracket_harvesting",
        "name": "0% long-term bracket gain harvesting",
        "tags": ["timing", "0% bracket", "basis", "low income"],
        "summary": "In a low-income year, realize long-term gains that fall in the "
                   "0% bracket — pay no federal tax and reset (step up) your basis.",
        "how_it_works": "If taxable income (incl. the gain) stays under the 0% "
                        "breakpoint ($48,350 single / $96,700 MFJ in 2025), the "
                        "long-term gain is taxed at 0%. Repurchasing immediately "
                        "raises basis with no wash-sale issue (it applies to losses).",
        "best_for": "Early retirees, gap years, students, sabbaticals, low-income years.",
        "caveats": "The gain itself counts as income and can push other income (e.g. "
                   "Social Security taxation, ACA subsidies) — model the full return.",
        "irc": "IRC §1(h)",
    },
    {
        "id": "specific_lot_id",
        "name": "Specific-lot identification",
        "tags": ["basis", "lot selection", "execution"],
        "summary": "When selling part of a position, choose high-basis lots to "
                   "minimize the realized gain (vs. default FIFO).",
        "how_it_works": "Instruct the broker to sell specific tax lots (e.g. highest "
                        "cost, or specific-ID) at trade time rather than first-in "
                        "first-out.",
        "best_for": "Positions accumulated over time at different prices.",
        "caveats": "Must elect at/before settlement; can't retroactively change lots.",
        "irc": "Treas. Reg. §1.1012-1(c)",
    },
    {
        "id": "asset_location",
        "name": "Asset location & tax-advantaged accounts",
        "tags": ["accounts", "ira", "401k", "roth", "hsa", "deferral"],
        "summary": "Hold tax-inefficient or high-growth assets inside IRAs/401(k)s/"
                   "Roths/HSAs so gains are deferred or never taxed.",
        "how_it_works": "Gains inside traditional accounts are tax-deferred until "
                        "withdrawal (then ordinary income); Roth and HSA growth can "
                        "be fully tax-free. No capital-gains tax on trades inside.",
        "best_for": "Long-term investors; rebalancing without triggering gains.",
        "caveats": "Contribution limits, early-withdrawal penalties, and RMD rules "
                   "apply. Traditional withdrawals are ordinary income, not LTCG.",
        "irc": "IRC §401, §408, §223 (HSA)",
    },
    {
        "id": "reduce_magi_niit",
        "name": "Reduce MAGI to cut the 3.8% NIIT",
        "tags": ["niit", "magi", "deductions", "retirement"],
        "summary": "Lower modified AGI below the NIIT threshold (or shrink the excess) "
                   "with pre-tax retirement/HSA contributions and timing.",
        "how_it_works": "NIIT hits the lesser of investment income or MAGI over the "
                        "threshold; cutting MAGI shrinks the taxed amount. Pre-tax "
                        "401(k)/HSA/traditional IRA contributions reduce MAGI.",
        "best_for": "Taxpayers near the $200k/$250k NIIT thresholds.",
        "caveats": "Thresholds are not inflation-indexed, so more people cross them "
                   "each year. Coordinate with the gain-timing strategy.",
        "irc": "IRC §1411",
    },
    {
        "id": "primary_residence_121",
        "name": "Primary residence exclusion (§121)",
        "tags": ["real estate", "home", "exclusion"],
        "summary": "Exclude up to $250,000 ($500,000 married joint) of gain on the "
                   "sale of your main home.",
        "how_it_works": "Must have owned AND used the home as your main residence for "
                        "at least 2 of the last 5 years. Generally usable once every "
                        "2 years.",
        "best_for": "Homeowners with a large embedded gain in their primary home.",
        "caveats": "Gain above the exclusion is taxable; depreciation (e.g. home "
                   "office/rental period) is recaptured. Partial exclusions exist for "
                   "job/health moves.",
        "irc": "IRC §121",
    },
    {
        "id": "1031_exchange",
        "name": "1031 like-kind exchange",
        "tags": ["real estate", "deferral", "investment property"],
        "summary": "Defer gain on investment/business real estate by reinvesting "
                   "proceeds into like-kind replacement property.",
        "how_it_works": "Use a qualified intermediary; identify replacement(s) within "
                        "45 days and close within 180 days. Basis carries over, "
                        "deferring (not eliminating) the gain.",
        "best_for": "Real-estate investors trading up or consolidating property.",
        "caveats": "Real property only (post-2017). Strict deadlines; 'boot' (cash/"
                   "debt relief) is taxable. Deferred gain resurfaces on a later "
                   "taxable sale (unless stepped up at death).",
        "irc": "IRC §1031",
    },
    {
        "id": "qof_opportunity_zone",
        "name": "Qualified Opportunity Zone (QOF) investment",
        "tags": ["deferral", "exclusion", "real estate", "reinvestment"],
        "summary": "Defer a realized gain by reinvesting it in a Qualified "
                   "Opportunity Fund, and exclude the QOF's own appreciation if held "
                   "10+ years.",
        "how_it_works": "Reinvest the gain in a QOF within 180 days to defer it; after "
                        "a 10-year hold, appreciation on the QOF investment is tax-free.",
        "best_for": "Investors with a large gain willing to commit capital long-term.",
        "caveats": "Program rules and deferral end-dates have changed over time — "
                   "verify current law. Illiquid; investment risk in the fund itself.",
        "irc": "IRC §1400Z-2",
    },
    {
        "id": "qsbs_1202",
        "name": "Qualified Small Business Stock (QSBS) exclusion",
        "tags": ["startup", "exclusion", "stock", "founders"],
        "summary": "Exclude a large share (up to 100%) of gain on qualified small "
                   "business C-corp stock held long enough.",
        "how_it_works": "Original-issue C-corp stock from a company with assets under "
                        "the statutory cap, held for the required multi-year period, "
                        "can exclude gain up to the greater of a dollar cap or a "
                        "multiple of basis.",
        "best_for": "Founders, early employees, and startup investors.",
        "caveats": "Many requirements (entity type, asset size, holding period, "
                   "qualified trade). Rules were expanded by recent legislation — "
                   "confirm the holding period and caps that apply to the shares.",
        "irc": "IRC §1202",
    },
    {
        "id": "donate_appreciated",
        "name": "Donate appreciated securities",
        "tags": ["charity", "donation", "avoid gain", "deduction"],
        "summary": "Gift long-term appreciated stock directly to charity: skip the "
                   "capital-gains tax entirely and deduct the full fair market value.",
        "how_it_works": "Charity receives the shares and sells them tax-free; you "
                        "avoid the gain and (if itemizing) deduct FMV, subject to AGI "
                        "limits.",
        "best_for": "Charitably inclined donors holding appreciated long-term positions.",
        "caveats": "Must be long-term holdings; FMV deduction for public stock is "
                   "limited to 30% of AGI (excess carries forward 5 years). Donating "
                   "losers is worse than selling them and donating cash.",
        "irc": "IRC §170",
    },
    {
        "id": "donor_advised_fund",
        "name": "Donor-advised fund (DAF) bunching",
        "tags": ["charity", "deduction", "timing", "bunching"],
        "summary": "Contribute appreciated stock to a DAF in a high-income year for a "
                   "big deduction now, then grant to charities over time.",
        "how_it_works": "Front-load several years of giving (often appreciated shares) "
                        "into one year to clear the standard deduction, while granting "
                        "out gradually.",
        "best_for": "High-income or windfall years; people who give annually.",
        "caveats": "Contributions are irrevocable; sponsor fees apply.",
        "irc": "IRC §170",
    },
    {
        "id": "charitable_remainder_trust",
        "name": "Charitable remainder trust (CRT)",
        "tags": ["charity", "trust", "deferral", "income"],
        "summary": "Contribute a highly appreciated asset to a CRT, which sells it "
                   "tax-free, pays you an income stream, and leaves the remainder to "
                   "charity.",
        "how_it_works": "The trust sells without immediate gain, you get a partial "
                        "charitable deduction and lifetime/term payments (partly "
                        "taxable as they come out).",
        "best_for": "Large concentrated, low-basis positions; retirement income needs.",
        "caveats": "Irrevocable and complex; requires legal/tax setup. Payouts are "
                   "taxed under tiered rules.",
        "irc": "IRC §664",
    },
    {
        "id": "gift_to_family",
        "name": "Gift appreciated assets to lower-bracket family",
        "tags": ["gifting", "family", "0% bracket", "basis"],
        "summary": "Gift appreciated stock to a family member in the 0%/15% bracket "
                   "who can sell at a lower rate.",
        "how_it_works": "The recipient takes your carryover basis and holding period; "
                        "if their income is low, the gain may be taxed at 0% or 15%.",
        "best_for": "Funding adult children, parents, or gifting within the annual "
                    "gift-tax exclusion.",
        "caveats": "KIDDIE TAX can tax a child's unearned income at the parents' rate. "
                   "Loss assets keep a dual-basis rule. Watch gift-tax limits.",
        "irc": "IRC §1015, §1(g) (kiddie tax)",
    },
    {
        "id": "step_up_at_death",
        "name": "Step-up in basis at death",
        "tags": ["estate", "basis", "inheritance", "hold"],
        "summary": "Holding highly appreciated assets until death gives heirs a basis "
                   "step-up to fair market value, erasing the unrealized gain.",
        "how_it_works": "Inherited assets are revalued to FMV at the date of death, so "
                        "heirs can sell with little or no capital gain.",
        "best_for": "Elderly investors with low-basis, long-held assets they don't "
                    "need to sell.",
        "caveats": "Requires not selling during life (liquidity/concentration risk). "
                   "Estate-tax and state rules may apply; law could change.",
        "irc": "IRC §1014",
    },
    {
        "id": "installment_sale",
        "name": "Installment sale",
        "tags": ["timing", "spread", "deferral", "brackets"],
        "summary": "Spread a gain over multiple years by receiving the sale price in "
                   "installments, keeping each year's income lower.",
        "how_it_works": "Recognize gain proportionally as payments are received, "
                        "which can keep you in lower LTCG brackets and below the NIIT "
                        "threshold each year.",
        "best_for": "Sales of a business, real estate, or other assets to a buyer "
                    "paying over time.",
        "caveats": "Not available for publicly traded securities; buyer credit risk; "
                   "interest must be charged; depreciation recapture is taxed up front.",
        "irc": "IRC §453",
    },
    {
        "id": "timing_low_income_years",
        "name": "Time gains into low-income years / spread across years",
        "tags": ["timing", "brackets", "niit", "spread"],
        "summary": "Realize gains when your other income is low, and split large sales "
                   "across tax years to stay in lower brackets and below NIIT.",
        "how_it_works": "Because LTCG rates and the NIIT depend on total income, "
                        "shifting WHEN you sell changes the rate. Defer into a "
                        "retirement/gap year, or sell in tranches across Dec/Jan.",
        "best_for": "Anyone with discretion over sale timing and variable income.",
        "caveats": "Market risk of waiting; year-end settlement timing matters.",
        "irc": "IRC §1(h), §1411",
    },
    {
        "id": "loss_carryforward",
        "name": "Use capital-loss carryforwards",
        "tags": ["losses", "carryforward", "offset"],
        "summary": "Apply prior-year unused capital losses against this year's gains.",
        "how_it_works": "Net capital losses not used in the year they arose carry "
                        "forward indefinitely and offset future gains first, then up "
                        "to $3,000/yr of ordinary income.",
        "best_for": "Investors who harvested losses in down years.",
        "caveats": "Carryforwards are lost at death (individual); track them on "
                   "Schedule D year to year.",
        "irc": "IRC §1212",
    },
    {
        "id": "exchange_fund",
        "name": "Exchange fund / direct indexing (diversify without selling)",
        "tags": ["concentration", "diversification", "advanced", "deferral"],
        "summary": "Diversify a concentrated low-basis position without triggering a "
                   "taxable sale.",
        "how_it_works": "Exchange funds let you contribute concentrated stock for a "
                        "diversified pool (deferring gain, typically 7-year lock-up). "
                        "Direct indexing harvests losses to offset trimming the "
                        "position over time.",
        "best_for": "Executives/founders with a single large low-basis holding.",
        "caveats": "Exchange funds are illiquid, accredited-investor only, and carry "
                   "fees; carryover basis defers (not erases) the gain.",
        "irc": "IRC §721 (partnership contribution)",
    },
]


def _matches(entry: dict, query: str) -> bool:
    q = query.lower()
    hay = " ".join([
        entry["name"], entry["summary"], entry["how_it_works"],
        entry["best_for"], entry["caveats"], " ".join(entry["tags"]), entry["id"],
    ]).lower()
    return all(term in hay for term in q.split())


def tax_strategies(query: str | None = None, strategy_id: str | None = None) -> dict:
    """Retrieve capital-gains tax-reduction strategies from the knowledge bank.

    - ``strategy_id``: return one full strategy by id.
    - ``query``: free-text/keyword filter (matches name, tags, and text).
    - neither: return the reference facts plus a short index of all strategies.
    """
    if strategy_id:
        for s in STRATEGIES:
            if s["id"] == strategy_id:
                return {"strategy": s}
        raise ValueError(
            f"No strategy with id '{strategy_id}'. "
            f"Known ids: {[s['id'] for s in STRATEGIES]}"
        )

    if query:
        hits = [s for s in STRATEGIES if _matches(s, query)]
        return {"query": query, "match_count": len(hits), "strategies": hits}

    return {
        "facts": CAPITAL_GAINS_FACTS,
        "strategy_index": [
            {"id": s["id"], "name": s["name"], "summary": s["summary"]}
            for s in STRATEGIES
        ],
        "note": "Call again with a strategy_id for full detail, or a query to filter.",
    }
