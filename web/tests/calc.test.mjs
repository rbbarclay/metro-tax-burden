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
