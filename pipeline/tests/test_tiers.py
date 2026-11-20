import pytest

import tiers

SRC = {"source": "IRS", "url": "https://www.irs.gov/", "license": "public domain (17 U.S.C. § 105)"}


def test_tag_adds_fields_and_rejects_unknown_tier():
    assert tiers.tag({"value": 1}, "estimated", "x") == {"value": 1, "tier": "estimated", "method": "x"}
    with pytest.raises(ValueError):
        tiers.tag({"value": 1}, "guess", "x")


def test_method_entry_with_assumptions():
    m = tiers.method_entry("burden", [SRC], "2026-11", {"filing_status": "single"})
    assert m["assumptions"] == {"filing_status": "single"}
    assert tiers.check_methods("t", {"k": m}) == []


@pytest.mark.parametrize("field", tiers.INPUT_FIELDS)
def test_inputs_need_source_url_and_license(field):
    inp = {k: v for k, v in SRC.items() if k != field}
    errors = tiers.check_methods("t", {"k": tiers.method_entry("d", [inp], "2025")})
    assert errors == [f"t method k input 0: missing {field}"]


def test_check_value():
    methods = {"k": tiers.method_entry("d", [SRC], "2025")}
    assert tiers.check_value("w", {"value": 1, "tier": "scenario", "method": "k"}, methods) == []
    assert tiers.check_value("w", {"value": None, "status": "not_covered"}, methods,
                             allow_untagged_status=("not_covered",)) == []
    assert tiers.check_value("w", {"value": None, "status": "not_covered"}, methods)  # not allowed by default
    assert tiers.check_value("w", {"value": 1, "tier": "observed"}, methods)  # no method
    assert tiers.check_value("w", {"value": 1, "tier": "observed", "method": "nope"}, methods)  # undefined method
