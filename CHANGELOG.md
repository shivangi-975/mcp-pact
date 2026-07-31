# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-31

### Added

- Consumer contract loading from YAML/JSON
- Provider surface loading from MCP `tools/list` snapshots
- `mcp-pact verify` for single-consumer checks
- `mcp-pact can-deploy` for multi-consumer release gates
- `mcp-pact diff` with optional consumer impact analysis
- `mcp-pact fuzz` for schema-derived adversarial argument cases
- Pytest plugin fixtures (`mcp_can_i_deploy`, …)
- Python API exports for library use
