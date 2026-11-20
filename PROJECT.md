# PROJECT.md

## Purpose

Estimate the total state and local tax burden a household would pay in each U.S. metro area, shown as dollars, effective rate, and hours of work. Plan: [docs/plans/v1.md](docs/plans/v1.md). Build plan: [docs/plans/v1-build.md](docs/plans/v1-build.md).

## Current state

- **M0 scaffolding done (2026-11-20).** Folder structure, CLAUDE.md, PROJECT.md, DATA.md, `.gitignore`, `pipeline/` (requirements, empty `tests/`), `web/` (placeholder `index.html`, `package.json`, `tests/`), and the GitHub Pages workflow. No data or calculations yet.
- `web/tests/site.test.mjs` checks that the page carries the "Estimate for planning. Not tax advice." note (plan section 8).
- **M1 data schema done (2026-11-20).** `pipeline/tiers.py` is copied from time-to-afford, with one addition: every method input must name its `source`, `url` and `license`. `pipeline/taxtables.py` validates the hand-entered tax tables in `data/tax/<year>/*.yml`:
  - Each table needs `kind`, `jurisdiction`, `tax_year` (must be 2026) and a `methods` table.
  - `income_tax` tables have exactly `single` and `married_joint`. Each has a `standard_deduction`, a `personal_exemption` and `brackets`, and every value carries a tier and a method.
  - Bracket rows are `{over, rate}`. The first row starts at 0, thresholds increase, and rates run from 0 to under 1. An empty list means no tax on wages.
  - Other kinds (FICA, sales, local, property) get their checks in the milestones that need them.
  - **Snapshot:** the canonical JSON of each table is hashed into `pipeline/tests/snapshots/tax_tables.json`. Tests fail if any table changes, appears or disappears until `.venv/bin/python pipeline/taxtables.py --update-snapshot` is run and committed (plan section 7). Comments and formatting don't change the hash.
  - No real tables yet; they come in M2. The CI pytest step no longer tolerates "no tests collected."
- **M2 part 1 done: federal and FICA (2026-11-20).**
  - `data/tax/2026/federal.yml`: 2026 brackets and standard deductions from Rev. Proc. 2025-32; personal exemption $0.
  - `data/tax/2026/fica.yml`: Social Security 6.2% up to $184,500, Medicare 1.45%, Additional Medicare 0.9% over $200,000 single / $250,000 joint.
  - `taxtables.py` adds the `fica` table type, and `--build` writes `web/data/tax-2026.json` (tables keyed by jurisdiction and kind). The tests fail if that bundle falls out of sync with the YAML.
  - `web/calc.js` has `bracketTax`, `taxableIncome`, `incomeTax` (works for any income_tax table, federal or state) and `fica`. Tests check tax at every bracket threshold against the base amounts printed in Rev. Proc. 2025-32, plus FICA examples.
  - Next: state income tax tables and the metro-to-state mapping, then the wage fallback.
- **M2 part 2: first state tables (2026-11-20).** Eleven tables now: federal, FICA, and nine states.
  - No wage tax: AK, SD, WA.
  - Flat, 2026 figures: PA (3.07%, no deductions); KY (3.5% per KRS 141.020(2)(f), $3,360 standard deduction); IL (4.95%, $2,925 exemption per person, none above $250,000/$500,000 AGI, a 2025 limit).
  - Graduated: NJ (current schedules, $1,000 exemption per person); KS and MO (all 2025 figures).
  - **Format additions:**
    - Per-value `year`: 2025 marks a prior-year fallback (plan 13.12).
    - Optional `personal_exemption_income_limit`.
    - Optional published `base` per bracket row. Missouri's chart rounds its bases, and NJ's Table B has a 50-cent step, so adding rates up from zero can't reproduce either.
  - **Tests:** KS and NJ against official tax-table rows; MO against the 2025 Tax Chart's worked examples; NJ against every row of its rate schedules. PA, KY and IL are checked by hand from the published rate and deductions. Worksheet tests for these are pending until the 2026 forms are out.
  - **Labeled `estimated`:** the KY joint-return standard deduction (assumed one per return) and MO's lack of a personal exemption. Neither was confirmed against the return instructions.
  - **Pilot states still to do:** NY (needs its high-income recapture worksheets), OH (2026 thresholds and exemptions are inflation-adjusted; DOR site unreachable), MI (indexed exemption; DOR site returns 403), MD (lower brackets and exemption phase-out), DE, IN, OR (federal tax subtraction and exemption credit), TX (official source still to confirm). The other no-tax states (FL, NV, NH, TN, WY) and the remaining states follow in M8.
- Check tables and rebuild the site bundle: `.venv/bin/python pipeline/taxtables.py --build` (add `--update-snapshot` after a deliberate table change)
- Setup: `uv venv .venv && uv pip install -p .venv -r pipeline/requirements.txt`
- Tests: `.venv/bin/pytest pipeline` and `cd web && node --test tests/`
- Local preview: `python3 -m http.server -d web` and open http://localhost:8000

## Decisions

Full list in plan section 13. In short:

- **Architecture:** static site, same shape as time-to-afford. A Python pipeline writes JSON; plain HTML, CSS and JavaScript with no framework, build step or npm packages. All tax math runs in the browser in `web/calc.js`.
- **Tiers:** every value carries `tier` (`observed`, `estimated`, `scenario`), a `method` key into a `methods` table, and source, license and as-of fields, as in time-to-afford.
- **Deductions:** standard deduction and personal exemption only; no itemized deductions, SALT deduction or credits.
- **Wage:** user-entered (hourly, or annual ÷ 2,080), otherwise the metro's OEWS median hourly wage, clearly labeled.
- **Filing status:** Single (default) or Married filing jointly.
- **Tax year:** 2026, with ACS 2025 1-year data; the mismatch is labeled.
- **Renters:** $0 property tax, with a note that some may be passed through in rent.
- **Taxable spending:** required for sales tax; no default.
- **Metros spanning states:** state picker within the metro, defaulting to the principal city's state.
- **Local income tax:** county-level taxes population-weighted; city-level taxes at the principal city's rate, labeled.
- **Coverage:** 10-metro pilot, then all 393 ACS 1-year metros for the base components, then sales and local income tax state by state ("not yet covered" until done).
- **Personal exemption credits (decided 2026-11-20):** where a state gives its personal exemption as a credit (e.g. California), it is applied as part of the personal exemption, an exception to excluding credits; the methodology page lists those states (plan 13.10).
- **One earner (decided 2026-11-20):** the wage is one earner's pay; Married filing jointly means a single-earner couple, so FICA and the Social Security wage base apply to that one wage. Labeled in results; a second-earner input may come later (plan 13.11).
- **Prior-year fallback (decided 2026-11-20):** where a state hasn't published a 2026 figure, the 2025 figure is used as is and labeled; each value records its year (plan 13.12, amends 13.4).
- **Tax tables are hand-entered YAML (decided 2026-11-20),** not downloaded, because tax law comes as PDFs, worksheets and statutes. YAML lets each figure carry a comment citing its page or line. The pipeline validates them and hashes their parsed content for the snapshot test.
- **Privacy:** user inputs never leave the browser or go into URLs.
- **License:** MIT for code; data under each source's terms (DATA.md).
- **Hosting:** GitHub Pages via `.github/workflows/pages.yml`, tests first, publishing `web/` without tests and `package.json`.

## To-do

- [x] M0: Scaffolding
- [x] M1: Data schema (tiers, tax year, filing status, snapshot-hash test)
- [ ] M2: Federal, FICA and state income tax, with worksheet tests; metro-to-state mapping; wage fallback
  - [x] Federal income tax and FICA (2026), tested against IRS figures
  - [ ] State income tax (and list which states give exemption credits): 9 done (AK, SD, WA, PA, KY, IL, NJ, KS, MO); exemption-credit states found so far: IA, UT, DE, OR
  - [ ] Metro-to-state mapping
  - [ ] Median-wage fallback (OEWS)
- [ ] M3: Property tax (ACS B25103 ÷ B25077), pilot metros
- [ ] M4: Sales tax, pilot metros
- [ ] M5: Local income tax, pilot metros
- [ ] M6: Burden calculation
- [ ] M7: Front end and methodology page
- [ ] M8: National base, all 393 metros
- [ ] M9: State-by-state rollout of sales and local income tax
- [x] Enable GitHub Pages for the repo (first deploy succeeded 2026-11-20)

## Open questions

See plan section 12.
