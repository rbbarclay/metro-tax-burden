# PROJECT.md

## Purpose

Estimate the total state and local tax burden a household would pay in each U.S. metro area, shown as dollars, effective rate, and hours of work. Plan: [docs/plans/v1.md](docs/plans/v1.md). Build plan: [docs/plans/v1-build.md](docs/plans/v1-build.md).

## Current state

- **M0 scaffolding done (2026-11-20).** Folder structure, CLAUDE.md, PROJECT.md, DATA.md, `.gitignore`, `pipeline/` (requirements, empty `tests/`), `web/` (placeholder `index.html`, `package.json`, `tests/`), and the GitHub Pages workflow. No data or calculations yet.
- The one test so far (`web/tests/site.test.mjs`) checks that the page carries the "Estimate for planning. Not tax advice." note (plan section 8). The workflow's pytest step accepts "no tests collected" until M1 adds pipeline tests.
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
- **Privacy:** user inputs never leave the browser or go into URLs.
- **License:** MIT for code; data under each source's terms (DATA.md).
- **Hosting:** GitHub Pages via `.github/workflows/pages.yml`, tests first, publishing `web/` without tests and `package.json`.

## To-do

- [x] M0: Scaffolding
- [ ] M1: Data schema (tiers, tax year, filing status, snapshot-hash test)
- [ ] M2: Federal, FICA and state income tax, with worksheet tests; metro-to-state mapping; wage fallback
- [ ] M3: Property tax (ACS B25103 ÷ B25077), pilot metros
- [ ] M4: Sales tax, pilot metros
- [ ] M5: Local income tax, pilot metros
- [ ] M6: Burden calculation
- [ ] M7: Front end and methodology page
- [ ] M8: National base, all 393 metros
- [ ] M9: State-by-state rollout of sales and local income tax
- [ ] Enable GitHub Pages for the repo (Settings → Pages → Source: GitHub Actions)

## Open questions

See plan section 12.
