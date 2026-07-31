# Examples

Sample consumer contracts and provider surfaces used by the test suite and README.

| File | Purpose |
| --- | --- |
| `consumer_support_agent.yaml` | Agent contract for a docs MCP server (`search_docs`, `get_doc`) |
| `provider_v1.json` | Compatible provider surface — verify / can-deploy should pass |
| `provider_v2_breaking.json` | Breaking evolution (tool removed, new required arg) — should fail |

## Try it

Compatible provider (exit `0`):

```bash
mcp-pact verify \
  --contract examples/consumer_support_agent.yaml \
  --provider examples/provider_v1.json

mcp-pact can-deploy \
  --provider examples/provider_v1.json \
  --contracts examples/consumer_support_agent.yaml
```

Breaking provider (exit `1` — `get_doc` removed, `space` newly required):

```bash
mcp-pact can-deploy \
  --provider examples/provider_v2_breaking.json \
  --contracts examples/consumer_support_agent.yaml
```

Surface diff with consumer impact:

```bash
mcp-pact diff \
  --old examples/provider_v1.json \
  --new examples/provider_v2_breaking.json \
  --contracts examples/consumer_support_agent.yaml
```

Generate schema fuzz cases:

```bash
mcp-pact fuzz --provider examples/provider_v1.json --out /tmp/fuzz_cases.json
```
