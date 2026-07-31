# mcp-pact

[![PyPI version](https://img.shields.io/pypi/v/mcp-pact.svg)](https://pypi.org/project/mcp-pact/)
[![Python versions](https://img.shields.io/pypi/pyversions/mcp-pact.svg)](https://pypi.org/project/mcp-pact/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/shivangi-975/mcp-pact/actions/workflows/ci.yml/badge.svg)](https://github.com/shivangi-975/mcp-pact/actions/workflows/ci.yml)

Consumer-driven contract testing for [MCP](https://modelcontextprotocol.io/) servers.

Agents declare the tools and arguments they depend on. CI verifies that a server surface still satisfies those contracts before you deploy.

## Why

Most MCP tooling snapshots the **provider** and diffs schemas. That answers “did the server change?”

`mcp-pact` answers a different question:

> If I ship this MCP server change, which **agents** break?

## Install

```bash
pip install mcp-pact
```

Requires Python 3.10+.

## Quickstart

### 1. Write a consumer contract

```yaml
# contracts/support_agent.yaml
consumer: support-agent
provider: docs-mcp
interactions:
  - tool: search_docs
    arguments: { query: "refund policy", limit: 5 }
    required_arguments: [query]
  - tool: get_doc
    arguments: { doc_id: "POL-12" }
    required_arguments: [doc_id]
```

### 2. Snapshot the provider surface

Export your MCP `tools/list` result to JSON (see [`examples/provider_v1.json`](examples/provider_v1.json)).

### 3. Verify in CI

```bash
# one consumer
mcp-pact verify \
  --contract examples/consumer_support_agent.yaml \
  --provider examples/provider_v1.json

# all consumers before release
mcp-pact can-deploy \
  --provider examples/provider_v1.json \
  --contracts contracts/*.yaml

# schema diff + consumer impact
mcp-pact diff \
  --old examples/provider_v1.json \
  --new examples/provider_v2_breaking.json \
  --contracts examples/consumer_support_agent.yaml

# generate adversarial argument cases from schemas
mcp-pact fuzz --provider examples/provider_v1.json --out fuzz_cases.json
```

Exit code `1` means at least one consumer would break.

## What is checked?

| Check | Breaking when |
| --- | --- |
| Tool presence | Consumer tool is missing on the provider |
| Required args | Consumer needs an argument the provider removed |
| Provider-required args | Provider newly requires an argument the consumer never sends |
| Types | Provider input type no longer accepts what the consumer sends |
| Description-only | Classified as `routing` (agent selection risk); not a hard fail by default |

## Python API

```python
from mcp_pact import (
    load_consumer_contract,
    load_provider_surface,
    can_i_deploy,
    generate_fuzz_cases,
)

provider = load_provider_surface("provider.json")
contract = load_consumer_contract("agent.yaml")
decision = can_i_deploy(provider, [contract])
assert decision.ok, decision.to_dict()
```

## Pytest plugin

```bash
pytest --mcp-provider-surface=provider.json \
       --mcp-consumer-contracts=contracts/a.yaml,contracts/b.yaml
```

```python
def test_agents_still_compatible(mcp_can_i_deploy):
    assert mcp_can_i_deploy.ok, mcp_can_i_deploy.to_dict()
```

## Comparison

| Library | Model |
| --- | --- |
| `mcp-contract`, `mcp-diff`, … | Provider snapshot + schema lockfile |
| **mcp-pact** | Consumer-driven contracts, can-i-deploy, fuzz case generation |

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Status

Alpha (`0.1.0`). Offline-first: works on committed JSON/YAML provider surfaces. Live MCP probing is planned.

## License

[MIT](LICENSE)
