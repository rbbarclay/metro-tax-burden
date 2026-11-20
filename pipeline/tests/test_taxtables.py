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


FICA = {
    "kind": "fica",
    "jurisdiction": "US",
    "tax_year": 2026,
    "methods": VALID["methods"],
    "social_security": {"rate": {"value": 0.062, "tier": "observed", "method": "xx_2026"},
                        "wage_base": {"value": 100000, "tier": "observed", "method": "xx_2026"}},
    "medicare": {"rate": {"value": 0.0145, "tier": "observed", "method": "xx_2026"},
                 "additional_rate": {"value": 0.009, "tier": "observed", "method": "xx_2026"}},
    "filing_status": {s: {"additional_medicare_threshold": {"value": 200000, "tier": "observed", "method": "xx_2026"}}
                      for s in taxtables.FILING_STATUSES},
}


def test_valid_fica_passes():
    assert taxtables.check_table("f", FICA) == []


@pytest.mark.parametrize("change, message", [
    (lambda t: t.pop("social_security"), "missing social_security"),
    (lambda t: t["social_security"]["rate"].update(value=6.2), "fraction from 0 to under 1"),
    (lambda t: t["medicare"].pop("additional_rate"), "medicare.additional_rate: missing"),
    (lambda t: t["filing_status"]["single"].clear(), "single.additional_medicare_threshold: missing"),
])
def test_invalid_fica_is_rejected(change, message):
    t = copy.deepcopy(FICA)
    change(t)
    errors = taxtables.check_table("f", t)
    assert any(message in e for e in errors), errors


def test_bundle_groups_by_jurisdiction_and_kind(tmp_path):
    root = tmp_path / "tax"
    write(root, "2026/federal.yml", {**VALID, "jurisdiction": "US"})
    write(root, "2026/fica.yml", FICA)
    write(root, "2026/xx.yml", VALID)
    bundle = taxtables.build_bundle(root)
    assert bundle["tax_year"] == 2026
    assert set(bundle["tables"]) == {"US", "state:XX"}
    assert set(bundle["tables"]["US"]) == {"income_tax", "fica"}

    write(root, "2026/xx2.yml", VALID)
    with pytest.raises(ValueError, match="second income_tax table for state:XX"):
        taxtables.build_bundle(root)


def test_bundle_out_of_date_is_reported(tmp_path):
    root, web = tmp_path / "tax", tmp_path / "web"
    write(root, "2026/xx.yml", VALID)
    assert taxtables.check_bundle(root, web_data=web)
    web.mkdir()
    taxtables.bundle_path(web_data=web).write_text(taxtables.bundle_json(taxtables.build_bundle(root)))
    assert taxtables.check_bundle(root, web_data=web) == []


def test_repo_tables_are_valid_match_snapshot_and_bundle():
    assert taxtables.check_all() == []
    assert taxtables.check_snapshot() == []
    assert taxtables.check_bundle() == []
