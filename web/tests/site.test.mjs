import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// Plan section 8: every page keeps a visible "not tax advice" note.
const NOTE = 'Estimate for planning. Not tax advice.';

test('index.html carries the not-tax-advice note', () => {
  const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.ok(html.includes(NOTE));
});
