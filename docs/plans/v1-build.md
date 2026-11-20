# Build plan: Metro tax burden, v1

Status: proposed. Last updated: 2026-11-20.

How the [v1 plan](v1.md) gets built. Decisions referenced as "13.x" are in section 13 of that plan.

## Architecture

Same shape as time-to-afford:

- A Python pipeline downloads public data, validates it, and writes JSON.
- A static site in plain HTML, CSS and JavaScript (no framework, build step or npm packages) reads one bundle, `web/data/metros.json`, plus the tax tables.
- **All tax math runs in the browser** in `web/calc.js`, tested with `node --test`. This keeps wage, filing status, housing choice and spending in the browser (plan section 10) and means each calculation exists once. Python builds and checks the tables but doesn't compute anyone's tax.
- Hosting on GitHub Pages; the workflow runs Python and JS tests before deploying.
- Helpers such as `tiers.py` and the ACS summary-file reader are copied from time-to-afford, not imported.

## Pilot metros

Ten metros, chosen to cover each local tax type and the no-income-tax cases:

| Metro | Why |
|---|---|
| New York | NYC income tax |
| Philadelphia | City wage tax, PA earned income tax |
| Columbus | Ohio municipal income tax |
| Detroit | Michigan city income tax |
| Baltimore | Maryland county income tax |
| Louisville | Kentucky occupational license tax |
| Kansas City | Missouri earnings tax, two-state metro |
| Portland, OR | Oregon city and regional income taxes, two-state metro |
| Seattle | No income tax, high sales tax |
| Houston | No income tax, high property tax |

## Milestones

Each milestone ends with tests passing, PROJECT.md updated, and a commit.

### M0: Scaffolding
- CLAUDE.md, PROJECT.md, DATA.md, `.gitignore`, `pipeline/` with `requirements.txt` and `tests/`, `web/` with `tests/`, Pages workflow.

### M1: Data schema (plan 11.1)
- Every value carries `tier`, `method`, and source, license and as-of fields through a `methods` table, as in time-to-afford.
- Every tax table carries `tax_year` (2026, per 13.4) and values for each filing status in v1: `single` and `married_joint` (13.3).
- Income tax tables store brackets, standard deduction and personal exemption per filing status (13.1).
- Snapshot-hash test: changing any bracket table fails the build until the snapshot is updated on purpose (plan section 7).
- Validation rejects any value missing tier, method, tax year or source.

### M2: Federal, FICA and state income tax (plan 11.2)
- `calc.js`: `federalTax(wage, status)`, `fica(wage, status)`, `stateTax(state, wage, status)`. Each applies the standard deduction and personal exemption only; no itemized deductions or credits (13.1).
- Federal and FICA tested against IRS 2026 published figures.
- State order: the states with no wage income tax, then flat-tax states, then states with brackets. Each state gets at least one test from its revenue department's worksheet or published example, for both Single and Married filing jointly where one is published.
- Wage input: hourly, or annual ÷ 2,080. With no entry, each metro uses its OEWS median hourly wage, and results state this (13.2). This needs the OEWS wage file, built as in time-to-afford.

### M3: Property tax (plan 11.3)
- ACS 2025 1-year B25103 (median real estate taxes paid) ÷ B25077 (median home value) per metro, tier `observed` for the inputs and `estimated` for the rate.
- Owner scenario: rate × home value (metro median by default, editable).
- Renter: $0 with the pass-through note (13.5). Housing choice is an input.
- Cross-checked against Census tables for the 10 pilot metros.

### M4: Sales tax (plan 11.4)
- Combined state and local rate per county from state revenue department files, weighted by county population, tier `estimated`, labeled as an approximation.
- Applied only to user-entered annual taxable spending. With no entry, show "Enter taxable spending to calculate" for sales tax and for totals that include it (13.6).
- Each source's terms recorded in DATA.md before use.

### M5: Local income tax (plan 11.5)
- One entry per jurisdiction: rate, tax year, source URL, as-of date, and which metros and counties it covers. Each entry is checked against the ordinance before it goes in.
- Metro flag plus the list of included jurisdictions. Metros with none show "none listed."

### M6: Burden calculation (plan 11.6)
- Total = federal + FICA + state + local income + property + sales.
- Effective rate = total ÷ gross income; hours of work = total ÷ hourly wage, per month (plan section 3).
- Output states the wage source (entered or metro median), filing status, housing choice, tax year 2026, ACS 2025, and which components are missing or waiting for input.

### M7: Front end (plan 11.7)
- Inputs: wage (optional, with fallback label), filing status (default Single), housing choice (rent or own, home value), taxable spending (required for sales tax, no default).
- Metro picker and a results breakdown with tier badges and "How is this calculated?" panels.
- Methodology page: definitions, sources, limitations (excluded deductions and credits, renters' pass-through, period mismatch, sales tax approximation, local tax list coverage), privacy, and "Estimate for planning. Not tax advice."

## After v1
- Expand from 10 pilot metros to all metros.
- Head of household and Married filing separately.
- Itemized deductions and credits, if chosen (plan section 12).
- Payroll add-ons such as state paid leave programs.
