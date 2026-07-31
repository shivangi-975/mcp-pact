"""Pytest fixtures for MCP consumer-driven contracts."""

from __future__ import annotations

import pytest

from .consumer import load_consumer_contract
from .provider import load_provider_surface
from .verify import can_i_deploy


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("mcp-pact")
    group.addoption(
        "--mcp-provider-surface",
        action="store",
        default=None,
        help="Path to provider surface JSON for contract verification",
    )
    group.addoption(
        "--mcp-consumer-contracts",
        action="store",
        default=None,
        help="Comma-separated consumer contract paths",
    )


@pytest.fixture
def mcp_provider_surface(request: pytest.FixtureRequest):
    path = request.config.getoption("--mcp-provider-surface")
    if not path:
        pytest.skip("pass --mcp-provider-surface=...")
    return load_provider_surface(path)


@pytest.fixture
def mcp_consumer_contracts(request: pytest.FixtureRequest):
    raw = request.config.getoption("--mcp-consumer-contracts")
    if not raw:
        pytest.skip("pass --mcp-consumer-contracts=...")
    paths = [p.strip() for p in raw.split(",") if p.strip()]
    return [load_consumer_contract(p) for p in paths]


@pytest.fixture
def mcp_can_i_deploy(mcp_provider_surface, mcp_consumer_contracts):
    return can_i_deploy(mcp_provider_surface, mcp_consumer_contracts)
