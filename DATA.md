# Data sources and terms

Only public or clearly licensed sources are used, preferring primary government sources (plan section 9). Every value carries a tier (`observed`, `estimated`, `scenario`), a method, a tax year where relevant, and an as-of date. Missing data is shown as missing.

**"Checked"** means the URL, table or series ID, and terms were confirmed on the publisher's own site on the date shown. Anything not yet confirmed is marked **UNVERIFIED**.

## In use

### IRS: federal income tax, tax year 2026 (`data/tax/2026/federal.yml`)
- **Publisher:** Internal Revenue Service
- **Primary source:** Rev. Proc. 2025-32 (https://www.irs.gov/pub/irs-drop/rp-25-32.pdf), section 4.01 (tax rate tables: Table 1 for married filing jointly, Table 3 for unmarried individuals) and section 4.14 (standard deduction). The tests check that tax at every threshold equals the "$X plus Y% of the excess" base amount printed in section 4.01.
- **Cross-check:** IR-2025-103, Oct. 9, 2025 (https://www.irs.gov/newsroom/irs-releases-tax-inflation-adjustments-for-tax-year-2026-including-amendments-from-the-one-big-beautiful-bill): same thresholds and standard deductions; states that the personal exemption remains $0. The page is labeled "Historical Content" but covers tax year 2026.
- **Checked 2026-11-20** on irs.gov.
- **Terms:** U.S. government work (17 U.S.C. § 105). **UNVERIFIED:** no IRS page on reuse of its content was found (irs.gov/copyright returns 404).
- **Attribution text:** "Source: Internal Revenue Service"

### IRS: FICA, 2026 wages (`data/tax/2026/fica.yml`)
- **Publisher:** Internal Revenue Service
- **Sources:** Topic no. 751 (https://www.irs.gov/taxtopics/tc751; page updated 2026-11-09): employee Social Security 6.2%, Medicare 1.45%, and "For earnings in 2026, this base limit is $184,500." Additional Medicare Tax Q&A (https://www.irs.gov/businesses/small-businesses-self-employed/questions-and-answers-for-the-additional-medicare-tax): rate 0.9%, thresholds $200,000 single and $250,000 married filing jointly.
- **Checked 2026-11-20** on irs.gov.
- **Not confirmed with the original publisher:** SSA's wage base page (https://www.ssa.gov/oact/cola/cbb.html) refused automated access (HTTP 403), so the $184,500 wage base is the IRS's statement of it. Whether the Additional Medicare thresholds are indexed for inflation wasn't confirmed; the 2026 values are used as published.
- **Terms:** as for the IRS entry above.
- **Attribution text:** "Source: Internal Revenue Service"

## Planned

All **UNVERIFIED**: URLs, table IDs and terms must be checked on the publisher's site before use.

- **State revenue departments:** tax year 2026 income tax brackets, standard deductions and personal exemptions, plus worksheets or published examples for tests; sales tax rate files.
- **Local jurisdictions:** ordinances and rate notices for local income taxes (plan section 5).
- **BLS OEWS:** median hourly wage by metro, for the wage fallback.
- **Census ACS 1-year (2025):** B25103 median real estate taxes paid, B25077 median home value.
- **Census / OMB:** metro delineation file (metro → counties → states, principal cities); county population estimates for weighting.
