"""Tax tables: entered by hand from primary sources, validated, and snapshot-hashed.

Tables are YAML files under data/tax/<tax year>/ (YAML so each figure can carry
a comment citing the page or line it came from). Every table has:

    kind: income_tax
    jurisdiction: US            # or e.g. "state:OR"
    tax_year: 2026
    methods: {...}              # see tiers.py; inputs need source, url, license
    filing_status:
      single:
        standard_deduction: {value: 0, tier: observed, method: <key>}
        personal_exemption: {value: 0, tier: observed, method: <key>}
        brackets:
          value: [{over: 0, rate: 0.10}, {over: 12000, rate: 0.12}]
          tier: observed
          method: <key>
      married_joint: {...same fields...}

`brackets` rows give the rate on income over each threshold; an empty list
means no tax on wages. Only income_tax is defined so far; the other kinds
(FICA, sales, local, property) are added in the milestones that need them.

Plan section 7: an annual update must be deliberate. The canonical JSON of each
table is hashed into tests/snapshots/tax_tables.json, and the tests fail if any
table changes, appears or disappears until the snapshot is updated with
`--update-snapshot`. Comments and formatting don't affect the hash.

Run: .venv/bin/python pipeline/taxtables.py [--update-snapshot]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

import tiers

ROOT = Path(__file__).resolve().parents[1]
TABLES_DIR = ROOT / "data" / "tax"
SNAPSHOT = Path(__file__).resolve().parent / "tests" / "snapshots" / "tax_tables.json"

TAX_YEAR = 2026
FILING_STATUSES = ("single", "married_joint")


def table_paths(root: Path = TABLES_DIR) -> list[Path]:
    return sorted(root.rglob("*.yml"))


def load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_table(label: str, t: dict, tax_year: int = TAX_YEAR) -> list[str]:
    if not isinstance(t, dict):
        return [f"{label}: not a mapping"]
    errors = []
    if t.get("tax_year") != tax_year:
        errors.append(f"{label}: tax_year is {t.get('tax_year')!r}, expected {tax_year}")
    if not str(t.get("jurisdiction", "")).strip():
        errors.append(f"{label}: missing jurisdiction")
    kind = t.get("kind")
    if kind not in KIND_CHECKS:
        return errors + [f"{label}: unknown kind {kind!r}"]
    methods = t.get("methods")
    errors += tiers.check_methods(label, methods)
    errors += KIND_CHECKS[kind](label, t, methods if isinstance(methods, dict) else {})
    return errors


def _check_income_tax(label: str, t: dict, methods: dict) -> list[str]:
    fs = t.get("filing_status")
    if not isinstance(fs, dict) or set(fs) != set(FILING_STATUSES):
        return [f"{label}: filing_status must have exactly {', '.join(FILING_STATUSES)}"]
    errors = []
    for status in FILING_STATUSES:
        where = f"{label} {status}"
        entry = fs[status]
        if not isinstance(entry, dict):
            errors.append(f"{where}: not a mapping")
            continue
        for field in ("standard_deduction", "personal_exemption"):
            errors += _check_amount(f"{where}.{field}", entry.get(field), methods)
        errors += _check_brackets(f"{where}.brackets", entry.get("brackets"), methods)
    return errors


KIND_CHECKS = {"income_tax": _check_income_tax}


def _is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _check_tagged(where: str, v, methods: dict) -> list[str]:
    if not isinstance(v, dict):
        return [f"{where}: missing"]
    return tiers.check_value(where, v, methods)


def _check_amount(where: str, v, methods: dict) -> list[str]:
    errors = _check_tagged(where, v, methods)
    if not errors and not (_is_number(v.get("value")) and v["value"] >= 0):
        errors.append(f"{where}: value must be a non-negative number")
    return errors


def _check_brackets(where: str, v, methods: dict) -> list[str]:
    errors = _check_tagged(where, v, methods)
    if errors:
        return errors
    rows = v.get("value")
    if not isinstance(rows, list):
        return [f"{where}: value must be a list"]
    prev = None
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {"over", "rate"}:
            errors.append(f"{where}[{i}]: must have exactly over and rate")
            continue
        over, rate = row["over"], row["rate"]
        if not (_is_number(over) and over >= 0):
            errors.append(f"{where}[{i}]: over must be a non-negative number")
            continue
        if not (_is_number(rate) and 0 <= rate < 1):
            errors.append(f"{where}[{i}]: rate must be a fraction from 0 to under 1")
        if i == 0 and over != 0:
            errors.append(f"{where}[0]: first bracket must start at 0")
        if prev is not None and over <= prev:
            errors.append(f"{where}[{i}]: thresholds must increase")
        prev = over
    return errors


def table_hash(t: dict) -> str:
    canonical = json.dumps(t, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def current_hashes(root: Path = TABLES_DIR) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): table_hash(load(p)) for p in table_paths(root)}


def check_snapshot(root: Path = TABLES_DIR, snapshot: Path = SNAPSHOT) -> list[str]:
    saved = json.loads(snapshot.read_text()) if snapshot.exists() else {}
    current = current_hashes(root)
    errors = []
    for name in sorted(set(saved) | set(current)):
        if name not in current:
            errors.append(f"tax table removed: {name}")
        elif name not in saved:
            errors.append(f"tax table added: {name}")
        elif saved[name] != current[name]:
            errors.append(f"tax table changed: {name}")
    if errors:
        errors.append("If deliberate, run `.venv/bin/python pipeline/taxtables.py --update-snapshot` and commit the snapshot.")
    return errors


def check_all(root: Path = TABLES_DIR, tax_year: int = TAX_YEAR) -> list[str]:
    errors = []
    for p in table_paths(root):
        errors += check_table(p.relative_to(root).as_posix(), load(p), tax_year)
    return errors


def update_snapshot(root: Path = TABLES_DIR, snapshot: Path = SNAPSHOT) -> None:
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(json.dumps(current_hashes(root), indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--update-snapshot", action="store_true",
                    help="record the current tables as the accepted snapshot (only if they validate)")
    args = ap.parse_args(argv)
    errors = check_all()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if args.update_snapshot:
        update_snapshot()
        print(f"snapshot updated: {len(table_paths())} tables")
        return 0
    errors = check_snapshot()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"ok: {len(table_paths())} tables valid and match the snapshot")
    return 0


if __name__ == "__main__":
    sys.exit(main())
