from pathlib import Path

import pytest

from mcp_pact import (
    can_i_deploy,
    generate_fuzz_cases,
    load_consumer_contract,
    load_provider_surface,
    verify_consumer_against_provider,
)
from mcp_pact.diff import diff_provider_surfaces, impact_of_provider_change

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def test_consumer_passes_against_v1():
    provider = load_provider_surface(EXAMPLES / "provider_v1.json")
    contract = load_consumer_contract(EXAMPLES / "consumer_support_agent.yaml")
    result = verify_consumer_against_provider(contract, provider)
    assert result.ok, result.to_dict()
    assert result.checked_interactions == 2


def test_can_i_deploy_fails_on_breaking_v2():
    provider = load_provider_surface(EXAMPLES / "provider_v2_breaking.json")
    contract = load_consumer_contract(EXAMPLES / "consumer_support_agent.yaml")
    decision = can_i_deploy(provider, [contract])
    assert decision.ok is False
    reasons = " ".join(f.reason for f in decision.failures)
    assert "get_doc" in reasons  # removed tool
    assert "space" in reasons  # newly required


def test_diff_and_impact():
    old = load_provider_surface(EXAMPLES / "provider_v1.json")
    new = load_provider_surface(EXAMPLES / "provider_v2_breaking.json")
    surface = diff_provider_surfaces(old, new)
    assert surface.ok is False
    assert "get_doc" in surface.removed_tools

    contract = load_consumer_contract(EXAMPLES / "consumer_support_agent.yaml")
    impact = impact_of_provider_change(old, new, [contract])
    assert impact.ok is False
    assert any(not r.ok for r in impact.consumer_results)


def test_fuzz_cases_cover_missing_and_wrong_type():
    provider = load_provider_surface(EXAMPLES / "provider_v1.json")
    tool = provider.tools["search_docs"]
    cases = generate_fuzz_cases("search_docs", tool.input_schema)
    names = {c.name for c in cases}
    assert "valid_minimal" in names
    assert "missing_required_query" in names
    assert "wrong_type_query" in names
    assert "unexpected_property" in names
    reject = [c for c in cases if c.expect == "reject"]
    assert reject


def test_cli_verify_exit_codes(tmp_path):
    from mcp_pact.cli import main

    with pytest.raises(SystemExit) as ok:
        main(
            [
                "verify",
                "--contract",
                str(EXAMPLES / "consumer_support_agent.yaml"),
                "--provider",
                str(EXAMPLES / "provider_v1.json"),
            ]
        )
    assert ok.value.code == 0

    with pytest.raises(SystemExit) as bad:
        main(
            [
                "verify",
                "--contract",
                str(EXAMPLES / "consumer_support_agent.yaml"),
                "--provider",
                str(EXAMPLES / "provider_v2_breaking.json"),
            ]
        )
    assert bad.value.code == 1


def test_type_compatibility_widening():
    from mcp_pact.compat import is_type_compatible

    assert is_type_compatible({"type": ["string", "null"]}, {"type": "string"})
    assert not is_type_compatible({"type": "integer"}, {"type": "string"})
