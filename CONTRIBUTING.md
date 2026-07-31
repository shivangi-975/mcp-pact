# Contributing

Thanks for helping improve `mcp-pact`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Guidelines

- Keep changes focused and small
- Add or update tests for behavior changes
- Match existing code style (dataclasses, typed Python 3.10+)
- Do not commit secrets, credentials, or local env files

## Pull requests

1. Fork and create a branch
2. Make your change with tests
3. Open a PR describing the problem and the fix

## Reporting issues

Include:

- `mcp-pact` version
- Minimal contract + provider surface that reproduces the issue
- Expected vs actual output / exit code
