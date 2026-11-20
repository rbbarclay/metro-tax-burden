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
means no tax on wages. Rows may also carry `base`, the published tax at the
row's threshold ("$X plus Y% of the excess over $Z"); then every row must, and
the calculation uses the bases as published (some schedules round them or
step up at a threshold, which adding rates up from zero can't reproduce). A filing status may also have
`personal_exemption_income_limit`: above that income the exemption is $0.

Any value may carry `year: <tax_year - 1>` when the state hasn't published the
figure for the tax year yet (plan 13.12). It is used as is, not adjusted, and
the site labels it. Without `year`, a value is for the table's tax year.

    kind: fica
    social_security: {rate: <value>, wage_base: <value>}
    medicare: {rate: <value>, additional_rate: <value>}
    filing_status:
      single: {additional_medicare_threshold: <value>}
      married_joint: {...}

Sales, local and property kinds are added in the milestones that need them.

The site reads one JSON bundle per tax year, web/data/tax-<year>.json, keyed by
jurisdiction and kind. It is generated with `--build` and must stay in sync
with the YAML (tests check this).

Plan section 7: an annual update must be deliberate. The canonical JSON of each
table is hashed into tests/snapshots/tax_tables.json, and the tests fail if any
table changes, appears or disappears until the snapshot is updated with
`--update-snapshot`. Comments and formatting don't affect the hash.

Run: .venv/bin/python pipeline/taxtables.py [--update-snapshot] [--build]
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
WEB_DATA = ROOT / "web" / "data"

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
        if "personal_exemption_income_limit" in entry:
            errors += _check_amount(f"{where}.personal_exemption_income_limit",
                                    entry["personal_exemption_income_limit"], methods)
        errors += _check_brackets(f"{where}.brackets", entry.get("brackets"), methods)
    return errors


def _check_fica(label: str, t: dict, methods: dict) -> list[str]:
    errors = []
    ss, med = t.get("social_security"), t.get("medicare")
    if not isinstance(ss, dict):
        errors.append(f"{label}: missing social_security")
    else:
        errors += _check_rate(f"{label} social_security.rate", ss.get("rate"), methods)
        errors += _check_amount(f"{label} social_security.wage_base", ss.get("wage_base"), methods)
    if not isinstance(med, dict):
        errors.append(f"{label}: missing medicare")
    else:
        errors += _check_rate(f"{label} medicare.rate", med.get("rate"), methods)
        errors += _check_rate(f"{label} medicare.additional_rate", med.get("additional_rate"), methods)
    fs = t.get("filing_status")
    if not isinstance(fs, dict) or set(fs) != set(FILING_STATUSES):
        return errors + [f"{label}: filing_status must have exactly {', '.join(FILING_STATUSES)}"]
    for status in FILING_STATUSES:
        entry = fs[status] if isinstance(fs[status], dict) else {}
        errors += _check_amount(f"{label} {status}.additional_medicare_threshold",
                                entry.get("additional_medicare_threshold"), methods)
    return errors


KIND_CHECKS = {"income_tax": _check_income_tax, "fica": _check_fica}


def _is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _check_tagged(where: str, v, methods: dict) -> list[str]:
    if not isinstance(v, dict):
        return [f"{where}: missing"]
    errors = tiers.check_value(where, v, methods)
    if "year" in v and v["year"] not in (TAX_YEAR, TAX_YEAR - 1):
        errors.append(f"{where}: year must be {TAX_YEAR} or {TAX_YEAR - 1}, got {v['year']!r}")
    return errors


def _check_amount(where: str, v, methods: dict) -> list[str]:
    errors = _check_tagged(where, v, methods)
    if not errors and not (_is_number(v.get("value")) and v["value"] >= 0):
        errors.append(f"{where}: value must be a non-negative number")
    return errors


def _check_rate(where: str, v, methods: dict) -> list[str]:
    errors = _check_tagged(where, v, methods)
    if not errors and not (_is_number(v.get("value")) and 0 <= v["value"] < 1):
        errors.append(f"{where}: value must be a fraction from 0 to under 1")
    return errors


def _check_brackets(where: str, v, methods: dict) -> list[str]:
    errors = _check_tagged(where, v, methods)
    if errors:
        return errors
    rows = v.get("value")
    if not isinstance(rows, list):
        return [f"{where}: value must be a list"]
    prev = None
    with_base = bool(rows) and isinstance(rows[0], dict) and "base" in rows[0]
    keys = {"over", "rate", "base"} if with_base else {"over", "rate"}
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != keys:
            errors.append(f"{where}[{i}]: must have exactly {', '.join(sorted(keys))}")
            continue
        over, rate = row["over"], row["rate"]
        if with_base and not (_is_number(row["base"]) and row["base"] >= 0):
            errors.append(f"{where}[{i}]: base must be a non-negative number")
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


def bundle_path(tax_year: int = TAX_YEAR, web_data: Path = WEB_DATA) -> Path:
    return web_data / f"tax-{tax_year}.json"


def build_bundle(root: Path = TABLES_DIR, tax_year: int = TAX_YEAR) -> dict:
    """All tables for one tax year, as {"tax_year", "tables": {jurisdiction: {kind: table}}}."""
    tables: dict[str, dict] = {}
    for p in sorted((root / str(tax_year)).glob("*.yml")):
        t = load(p)
        slot = tables.setdefault(t["jurisdiction"], {})
        if t["kind"] in slot:
            raise ValueError(f"{p.name}: second {t['kind']} table for {t['jurisdiction']}")
        slot[t["kind"]] = t
    return {"tax_year": tax_year, "tables": tables}


def bundle_json(bundle: dict) -> str:
    return json.dumps(bundle, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def check_bundle(root: Path = TABLES_DIR, tax_year: int = TAX_YEAR, web_data: Path = WEB_DATA) -> list[str]:
    path = bundle_path(tax_year, web_data)
    if not path.exists() or path.read_text(encoding="utf-8") != bundle_json(build_bundle(root, tax_year)):
        return [f"{path.relative_to(ROOT) if path.is_relative_to(ROOT) else path} is out of date; "
                "run `.venv/bin/python pipeline/taxtables.py --build`"]
    return []


def update_snapshot(root: Path = TABLES_DIR, snapshot: Path = SNAPSHOT) -> None:
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(json.dumps(current_hashes(root), indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--update-snapshot", action="store_true",
                    help="record the current tables as the accepted snapshot (only if they validate)")
    ap.add_argument("--build", action="store_true",
                    help=f"write {bundle_path().relative_to(ROOT)} for the site (only if tables validate)")
    args = ap.parse_args(argv)
    errors = check_all()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if args.update_snapshot:
        update_snapshot()
        print(f"snapshot updated: {len(table_paths())} tables")
    if args.build:
        path = bundle_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(bundle_json(build_bundle()), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    errors = check_snapshot() + check_bundle()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"ok: {len(table_paths())} tables valid, match the snapshot, and the site bundle is current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
