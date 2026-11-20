import copy

import pytest
import yaml

import taxtables

# A made-up table: the schema is under test here, not real tax law.
VALID = {
    "kind": "income_tax",
    "jurisdiction": "state:XX",
    "tax_year": 2026,
    "methods": {
        "xx_2026": {
            "description": "Example brackets",
            "inputs": [{"source": "Example DOR", "url": "https://example.gov/", "license": "public domain"}],
            "as_of": "2025-12",
        }
    },
    "filing_status": {
        status: {
            "standard_deduction": {"value": 5000, "tier": "observed", "method": "xx_2026"},
            "personal_exemption": {"value": 0, "tier": "observed", "method": "xx_2026"},
            "brackets": {"value": [{"over": 0, "rate": 0.02}, {"over": 10000, "rate": 0.05}],
                         "tier": "observed", "method": "xx_2026"},
        }
        for status in taxtables.FILING_STATUSES
    },
}


def mutated(fn):
    t = copy.deepcopy(VALID)
    fn(t)
    return t


def single(t):
    return t["filing_status"]["single"]


def test_valid_table_passes():
    assert taxtables.check_table("t", VALID) == []


def test_no_income_tax_is_an_empty_bracket_list():
    t = mutated(lambda t: single(t)["brackets"].update(value=[]))
    assert taxtables.check_table("t", t) == []


@pytest.mark.parametrize("change, message", [
    (lambda t: t.update(tax_year=2025), "tax_year is 2025, expected 2026"),
    (lambda t: t.pop("jurisdiction"), "missing jurisdiction"),
    (lambda t: t.update(kind="vat"), "unknown kind 'vat'"),
    (lambda t: t.pop("methods"), "missing methods table"),
    (lambda t: t["filing_status"].pop("married_joint"), "filing_status must have exactly"),
    (lambda t: t["filing_status"].update(head_of_household={}), "filing_status must have exactly"),
    (lambda t: single(t).pop("personal_exemption"), "single.personal_exemption: missing"),
    (lambda t: single(t)["standard_deduction"].pop("tier"), "missing or invalid tier"),
    (lambda t: single(t)["standard_deduction"].update(method="other"), "not defined in methods table"),
    (lambda t: single(t)["standard_deduction"].update(value=-1), "non-negative number"),
    (lambda t: single(t)["standard_deduction"].update(value="5000"), "non-negative number"),
    (lambda t: single(t)["brackets"].update(value={"over": 0}), "value must be a list"),
    (lambda t: single(t)["brackets"]["value"][0].update(over=100), "first bracket must start at 0"),
    (lambda t: single(t)["brackets"]["value"][1].update(over=0), "thresholds must increase"),
    (lambda t: single(t)["brackets"]["value"][1].update(rate=5), "rate must be a fraction"),
    (lambda t: single(t)["brackets"]["value"][1].update(extra=1), "must have exactly over and rate"),
])
def test_invalid_tables_are_rejected(change, message):
    errors = taxtables.check_table("t", mutated(change))
    assert any(message in e for e in errors), errors


def write(root, name, table):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(table))
    return path


def test_snapshot_detects_change_addition_and_removal(tmp_path):
    root, snap = tmp_path / "tax", tmp_path / "snap.json"
    path = write(root, "2026/xx.yml", VALID)
    taxtables.update_snapshot(root, snap)
    assert taxtables.check_snapshot(root, snap) == []

    # Comments and formatting don't count as a change.
    path.write_text("# source: example\n" + yaml.safe_dump(VALID, indent=4))
    assert taxtables.check_snapshot(root, snap) == []

    write(root, "2026/xx.yml", mutated(lambda t: single(t)["brackets"]["value"][1].update(rate=0.06)))
    assert taxtables.check_snapshot(root, snap)[0] == "tax table changed: 2026/xx.yml"

    write(root, "2026/yy.yml", VALID)
    assert "tax table added: 2026/yy.yml" in taxtables.check_snapshot(root, snap)

    path.unlink()
    assert "tax table removed: 2026/xx.yml" in taxtables.check_snapshot(root, snap)


def test_repo_tables_are_valid_and_match_snapshot():
    assert taxtables.check_all() == []
    assert taxtables.check_snapshot() == []
