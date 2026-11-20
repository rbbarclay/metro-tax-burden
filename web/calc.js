// Pure calculation helpers for Metro Tax Burden. No DOM access, no storage, no network.
// Tables come from web/data/tax-<year>.json; every figure in them is {value, tier, method}.

export const HOURS_PER_YEAR = 2080; // 40 hours x 52 weeks
export const FILING_STATUSES = ["single", "married_joint"];

const v = (field) => field.value;

/**
 * Tax on `taxable` income under bracket rows [{over, rate}], each rate applying above its threshold.
 * Rows with a published `base` (tax at the threshold) use it as is: tax = base + rate x excess.
 */
export function bracketTax(rows, taxable) {
  if (rows.length && "base" in rows[0]) {
    const row = rows.findLast((r) => taxable > r.over) ?? rows[0];
    return taxable > row.over ? row.base + (taxable - row.over) * row.rate : row.base;
  }
  let tax = 0;
  rows.forEach((row, i) => {
    const top = i + 1 < rows.length ? rows[i + 1].over : Infinity;
    if (taxable > row.over) tax += (Math.min(taxable, top) - row.over) * row.rate;
  });
  return tax;
}

/** Personal exemption, or zero above the table's income limit if it has one. */
export function personalExemption(table, wage, status) {
  const fs = table.filing_status[status];
  const limit = fs.personal_exemption_income_limit;
  return limit && wage > v(limit) ? 0 : v(fs.personal_exemption);
}

/** Wage minus the standard deduction and personal exemption, never below zero. */
export function taxableIncome(table, wage, status) {
  const fs = table.filing_status[status];
  return Math.max(0, wage - v(fs.standard_deduction) - personalExemption(table, wage, status));
}

/** Income tax on annual wage income under an income_tax table (federal or state). */
export function incomeTax(table, wage, status) {
  return bracketTax(v(table.filing_status[status].brackets), taxableIncome(table, wage, status));
}

/**
 * Employee FICA on one earner's annual wage. The Additional Medicare threshold
 * depends on filing status; the Social Security wage base applies per earner.
 */
export function fica(table, wage, status) {
  const socialSecurity = Math.min(wage, v(table.social_security.wage_base)) * v(table.social_security.rate);
  const medicare = wage * v(table.medicare.rate);
  const threshold = v(table.filing_status[status].additional_medicare_threshold);
  const additionalMedicare = Math.max(0, wage - threshold) * v(table.medicare.additional_rate);
  return { socialSecurity, medicare, additionalMedicare, total: socialSecurity + medicare + additionalMedicare };
}
