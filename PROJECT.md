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
- Check tables: `.venv/bin/python pipeline/taxtables.py`
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
- **Tax tables are hand-entered YAML (decided 2026-11-20),** not downloaded, because tax law comes as PDFs, worksheets and statutes. YAML lets each figure carry a comment citing its page or line. The pipeline validates them and hashes their parsed content for the snapshot test.
- **Privacy:** user inputs never leave the browser or go into URLs.
- **License:** MIT for code; data under each source's terms (DATA.md).
- **Hosting:** GitHub Pages via `.github/workflows/pages.yml`, tests first, publishing `web/` without tests and `package.json`.

## To-do

- [x] M0: Scaffolding
- [x] M1: Data schema (tiers, tax year, filing status, snapshot-hash test)
- [ ] M2: Federal, FICA and state income tax, with worksheet tests; metro-to-state mapping; wage fallback
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
