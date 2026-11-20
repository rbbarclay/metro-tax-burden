import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { bracketTax, taxableIncome, incomeTax, fica } from "../calc.js";

const bundle = JSON.parse(readFileSync(new URL("../data/tax-2026.json", import.meta.url), "utf8"));
const federal = bundle.tables.US.income_tax;
const ficaTable = bundle.tables.US.fica;

// Allow for floating-point noise only.
const near = (actual, expected) => assert.ok(Math.abs(actual - expected) < 0.005, `${actual} != ${expected}`);

test("bracketTax applies each rate above its threshold", () => {
  const rows = [{ over: 0, rate: 0.1 }, { over: 100, rate: 0.2 }];
  near(bracketTax(rows, 0), 0);
  near(bracketTax(rows, 50), 5);
  near(bracketTax(rows, 150), 20);
  near(bracketTax([], 1e6), 0); // no tax on wages
});

test("bracketTax uses published bases when rows have them", () => {
  const rows = [{ over: 0, rate: 0, base: 0 }, { over: 100, rate: 0.1, base: 30 }];
  near(bracketTax(rows, 100), 0);
  near(bracketTax(rows, 101), 30.1); // steps up to the published base above the threshold
  near(bracketTax(rows, 50), 0);
});

// Rev. Proc. 2025-32, section 4.01: "$X plus Y% of the excess over $Z".
// Taxable income exactly at each threshold must give the printed base amount.
const IRS_BASES = {
  single: [[12400, 1240], [50400, 5800], [105700, 17966], [201775, 41024], [256225, 58448], [640600, 192979.25]],
  married_joint: [[24800, 2480], [100800, 11600], [211400, 35932], [403550, 82048], [512450, 116896], [768700, 206583.5]],
};

for (const [status, rows] of Object.entries(IRS_BASES)) {
  test(`federal 2026 ${status}: tax at each threshold matches Rev. Proc. 2025-32`, () => {
    const deduction = federal.filing_status[status].standard_deduction.value;
    for (const [threshold, base] of rows) near(incomeTax(federal, threshold + deduction, status), base);
  });
}

test("federal 2026: standard deduction and between-bracket income", () => {
  assert.equal(taxableIncome(federal, 16100, "single"), 0);
  assert.equal(incomeTax(federal, 10000, "single"), 0);
  // $75,000 taxable, single: $5,800 plus 22% of the excess over $50,400.
  near(incomeTax(federal, 75000 + 16100, "single"), 5800 + 0.22 * 24600);
  // $150,000 taxable, joint: $11,600 plus 22% of the excess over $100,800.
  near(incomeTax(federal, 150000 + 32200, "married_joint"), 11600 + 0.22 * 49200);
});

test("FICA 2026: rates, wage base and Additional Medicare threshold (IRS Topic 751 and Q&A)", () => {
  const low = fica(ficaTable, 50000, "single");
  near(low.socialSecurity, 3100); // 6.2%
  near(low.medicare, 725); // 1.45%
  near(low.additionalMedicare, 0);
  near(low.total, 3825);

  const high = fica(ficaTable, 300000, "single");
  near(high.socialSecurity, 184500 * 0.062); // capped at the $184,500 wage base: $11,439
  near(high.medicare, 4350);
  near(high.additionalMedicare, 900); // 0.9% over $200,000

  near(fica(ficaTable, 300000, "married_joint").additionalMedicare, 450); // 0.9% over $250,000
});

// ---- States. Published examples are quoted from the source named in each table's comments.
const state = (code) => bundle.tables[`state:${code}`].income_tax;
const within = (actual, expected, tol) => assert.ok(Math.abs(actual - expected) <= tol, `${actual} not within ${tol} of ${expected}`);

test("no-income-tax states tax nothing", () => {
  for (const code of ["AK", "SD", "WA"]) {
    for (const status of ["single", "married_joint"]) assert.equal(incomeTax(state(code), 250000, status), 0);
  }
});

test("Pennsylvania: 3.07% of all compensation, no deductions", () => {
  near(incomeTax(state("PA"), 60000, "single"), 1842);
  near(incomeTax(state("PA"), 60000, "married_joint"), 1842);
});

test("Kentucky 2026: 3.5% after the $3,360 standard deduction (KRS 141.020, DOR release)", () => {
  near(incomeTax(state("KY"), 60000, "single"), 0.035 * (60000 - 3360));
});

test("Illinois 2026: 4.95% after $2,925 per person; no exemption above the AGI limit", () => {
  near(incomeTax(state("IL"), 60000, "single"), 0.0495 * (60000 - 2925));
  near(incomeTax(state("IL"), 60000, "married_joint"), 0.0495 * (60000 - 5850));
  near(incomeTax(state("IL"), 250000, "single"), 0.0495 * (250000 - 2925)); // at the limit: allowed
  near(incomeTax(state("IL"), 250001, "single"), 0.0495 * 250001); // over $250,000: none
  near(incomeTax(state("IL"), 400000, "married_joint"), 0.0495 * (400000 - 5850));
});

test("New Jersey: matches the published 'multiply, then subtract' rate schedules", () => {
  const nj = state("NJ");
  // [taxable income, rate, subtraction] from each row of Tables A and B.
  const tableA = [[20000, 0.014, 0], [35000, 0.0175, 70], [40000, 0.035, 682.5], [75000, 0.05525, 1492.5],
    [500000, 0.0637, 2126.25], [1000000, 0.0897, 15126.25], [2000000, 0.1075, 32926.25]];
  const tableB = [[20000, 0.014, 0], [50000, 0.0175, 70], [70000, 0.0245, 420], [80000, 0.035, 1154.5],
    [150000, 0.05525, 2775], [500000, 0.0637, 4042.5], [1000000, 0.0897, 17042.5], [2000000, 0.1075, 34842.5]];
  // Check just inside the top of each row (the published rows are "over ... but not over").
  for (const [x, rate, sub] of tableA) near(bracketTax(nj.filing_status.single.brackets.value, x - 1), (x - 1) * rate - sub);
  for (const [x, rate, sub] of tableB) near(bracketTax(nj.filing_status.married_joint.brackets.value, x - 1), (x - 1) * rate - sub);
  // NJ tax table, $50,000-$50,050 row: single 1,271, joint 806 (table amounts are rounded).
  within(bracketTax(nj.filing_status.single.brackets.value, 50025), 1271, 1);
  within(bracketTax(nj.filing_status.married_joint.brackets.value, 50025), 806, 1);
  near(incomeTax(nj, 51000, "single"), bracketTax(nj.filing_status.single.brackets.value, 50000)); // $1,000 exemption
});

test("Kansas (2025 figures): 2025 tax table rows and deductions", () => {
  const ks = state("KS");
  // 2025 Kansas tax table, taxable income $62,301-$62,350: single 3,390, joint 3,303.
  within(bracketTax(ks.filing_status.single.brackets.value, 62325), 3390, 1);
  within(bracketTax(ks.filing_status.married_joint.brackets.value, 62325), 3303, 1);
  // $62,251-$62,300: single 3,388.
  within(bracketTax(ks.filing_status.single.brackets.value, 62275), 3388, 1);
  assert.equal(taxableIncome(ks, 50000, "single"), 50000 - 3605 - 9160);
  assert.equal(taxableIncome(ks, 50000, "married_joint"), 50000 - 8240 - 18320);
});

test("Missouri (2025 figures): 2025 Tax Chart worked examples and bracket bases", () => {
  const rows = state("MO").filing_status.single.brackets.value;
  near(bracketTax(rows, 3090), 37.6); // Example A: $26 + 2.5% x $464 = $37.60
  near(bracketTax(rows, 12000), 388.02); // Example B: $256 + 4.7% x $2,809 = $388.02
  for (const [x, base] of [[2626, 26], [3939, 59], [5252, 98], [6565, 144], [7878, 197], [9191, 256]]) {
    within(bracketTax(rows, x), base, 0.5); // chart bases are rounded to whole dollars
  }
  assert.equal(taxableIncome(state("MO"), 50000, "married_joint"), 50000 - 31500);
});
