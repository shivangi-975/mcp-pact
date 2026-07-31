# Examples

Sample consumer contracts and provider surfaces used by the test suite and README.

| File | Purpose |
| --- | --- |
| `consumer_support_agent.yaml` | Agent contract for a docs MCP server |
| `provider_v1.json` | Compatible provider surface |
| `provider_v2_breaking.json` | Breaking evolution (tool removed, new required arg) |

Try:

```bash
mcp-pact verify \
  --contract examples/consumer_support_agent.yaml \
  --provider examples/provider_v1.json

mcp-pact can-deploy \
  --provider examples/provider_v2_breaking.json \
  --contracts examples/consumer_support_agent.yaml
```
