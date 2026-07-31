"""CLI: mcp-pact."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .consumer import load_consumer_contract
from .diff import diff_provider_surfaces, impact_of_provider_change
from .fuzz import generate_fuzz_cases
from .provider import load_provider_surface
from .verify import can_i_deploy, verify_consumer_against_provider


def _load_contracts(paths: Sequence[str]):
    return [load_consumer_contract(p) for p in paths]


def cmd_verify(args: argparse.Namespace) -> int:
    provider = load_provider_surface(args.provider)
    contract = load_consumer_contract(args.contract)
    result = verify_consumer_against_provider(contract, provider)
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.ok else 1


def cmd_can_deploy(args: argparse.Namespace) -> int:
    provider = load_provider_surface(args.provider)
    contracts = _load_contracts(args.contracts)
    decision = can_i_deploy(provider, contracts)
    print(json.dumps(decision.to_dict(), indent=2))
    return 0 if decision.ok else 1


def cmd_diff(args: argparse.Namespace) -> int:
    old = load_provider_surface(args.old)
    new = load_provider_surface(args.new)
    if args.contracts:
        report = impact_of_provider_change(old, new, _load_contracts(args.contracts))
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.ok else 1
    report = diff_provider_surfaces(old, new)
    print(json.dumps(report.to_dict(), indent=2))
    return 0 if report.ok else 1


def cmd_fuzz(args: argparse.Namespace) -> int:
    provider = load_provider_surface(args.provider)
    all_cases = []
    for name, tool in sorted(provider.tools.items()):
        if args.tool and name != args.tool:
            continue
        all_cases.extend(generate_fuzz_cases(name, tool.input_schema))
    payload = {"count": len(all_cases), "cases": [c.to_dict() for c in all_cases]}
    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2) + "\n")
        print(f"Wrote {len(all_cases)} fuzz cases to {args.out}")
    else:
        print(json.dumps(payload, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mcp-pact",
        description=(
            "Consumer-driven contract testing for MCP servers. "
            "Verify agent contracts, gate releases with can-i-deploy, "
            "diff provider surfaces, and generate schema fuzz cases."
        ),
        epilog=(
            "Exit codes: 0 = compatible / success; "
            "1 = at least one consumer would break (verify, can-deploy, diff with contracts). "
            "fuzz always returns 0 on successful generation."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"mcp-pact {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    v = sub.add_parser(
        "verify",
        help="Verify one consumer contract against a provider surface",
        description="Check a single agent contract against an MCP provider tools/list snapshot.",
    )
    v.add_argument("--contract", required=True, help="Path to consumer contract YAML/JSON")
    v.add_argument("--provider", required=True, help="Path to provider surface JSON snapshot")
    v.set_defaults(func=cmd_verify)

    c = sub.add_parser(
        "can-deploy",
        help="Check whether provider satisfies all consumer contracts",
        description=(
            "Release gate: verify the provider surface against every consumer contract. "
            "Exits 0 only when all consumers remain compatible."
        ),
    )
    c.add_argument("--provider", required=True, help="Path to provider surface JSON snapshot")
    c.add_argument(
        "--contracts",
        nargs="+",
        required=True,
        help="One or more consumer contract paths (YAML/JSON)",
    )
    c.set_defaults(func=cmd_can_deploy)

    d = sub.add_parser(
        "diff",
        help="Diff two provider surfaces; optionally show consumer impact",
        description=(
            "Compare old vs new provider surfaces. With --contracts, also re-verify "
            "each consumer against the new surface and exit 1 on impact."
        ),
    )
    d.add_argument("--old", required=True, help="Previous provider surface JSON")
    d.add_argument("--new", required=True, help="Candidate provider surface JSON")
    d.add_argument(
        "--contracts",
        nargs="*",
        default=[],
        help="Optional consumer contracts for impact analysis",
    )
    d.set_defaults(func=cmd_diff)

    f = sub.add_parser(
        "fuzz",
        help="Generate schema fuzz cases from a provider surface",
        description="Derive deterministic accept/reject argument cases from tool input schemas.",
    )
    f.add_argument("--provider", required=True, help="Path to provider surface JSON snapshot")
    f.add_argument("--tool", default=None, help="Limit generation to a single tool name")
    f.add_argument("--out", default=None, help="Write JSON cases to this path (default: stdout)")
    f.set_defaults(func=cmd_fuzz)

    return p


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    code = args.func(args)
    sys.exit(code)


if __name__ == "__main__":
    main()
