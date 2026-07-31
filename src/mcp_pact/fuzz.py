"""Generate adversarial / invalid tool argument cases from a JSON Schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FuzzCase:
    tool: str
    name: str
    arguments: dict[str, Any]
    expect: str  # "reject" | "accept"
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "name": self.name,
            "arguments": self.arguments,
            "expect": self.expect,
            "rationale": self.rationale,
        }


def _example_for_schema(schema: dict[str, Any]) -> Any:
    t = schema.get("type", "string")
    if isinstance(t, list):
        t = t[0] if t else "string"
    if schema.get("enum"):
        return schema["enum"][0]
    if t == "string":
        return "sample"
    if t == "integer":
        return 1
    if t == "number":
        return 1.0
    if t == "boolean":
        return True
    if t == "array":
        return []
    if t == "object":
        return {}
    if t == "null":
        return None
    return "sample"


def _valid_base(schema: dict[str, Any]) -> dict[str, Any]:
    props = schema.get("properties") or {}
    required = schema.get("required") or []
    base: dict[str, Any] = {}
    for name in required:
        prop = props.get(name) if isinstance(props.get(name), dict) else {"type": "string"}
        base[name] = _example_for_schema(prop or {"type": "string"})
    return base


def generate_fuzz_cases(
    tool_name: str,
    input_schema: dict[str, Any],
    *,
    include_valid: bool = True,
) -> list[FuzzCase]:
    """Derive deterministic negative (and optional positive) cases from a tool schema.

    These cases are for *contract stability* of error handling: a provider should
    reject invalid inputs. The library does not call the server itself unless you
    wire the cases into a live runner.
    """
    props = input_schema.get("properties") or {}
    if not isinstance(props, dict):
        props = {}
    required = [str(x) for x in (input_schema.get("required") or [])]
    cases: list[FuzzCase] = []
    base = _valid_base(input_schema)

    if include_valid and (base or not required):
        cases.append(
            FuzzCase(
                tool=tool_name,
                name="valid_minimal",
                arguments=dict(base),
                expect="accept",
                rationale="Minimal payload satisfying required properties",
            )
        )

    # Missing each required field
    for req in required:
        bad = {k: v for k, v in base.items() if k != req}
        cases.append(
            FuzzCase(
                tool=tool_name,
                name=f"missing_required_{req}",
                arguments=bad,
                expect="reject",
                rationale=f"Omits required argument {req!r}",
            )
        )

    # Wrong type for each property
    wrong = {
        "string": 123,
        "integer": "not-an-int",
        "number": "not-a-number",
        "boolean": "yes",
        "array": {},
        "object": [],
    }
    for name, prop in props.items():
        if not isinstance(prop, dict):
            continue
        t = prop.get("type", "string")
        if isinstance(t, list):
            t = next((x for x in t if x != "null"), t[0] if t else "string")
        if t not in wrong:
            continue
        payload = dict(base)
        payload[name] = wrong[t]
        cases.append(
            FuzzCase(
                tool=tool_name,
                name=f"wrong_type_{name}",
                arguments=payload,
                expect="reject",
                rationale=f"Sends {type(wrong[t]).__name__} for {name!r} expecting {t}",
            )
        )

    # Unknown property (if additionalProperties is false)
    if input_schema.get("additionalProperties") is False:
        payload = dict(base)
        payload["__unexpected__"] = "x"
        cases.append(
            FuzzCase(
                tool=tool_name,
                name="unexpected_property",
                arguments=payload,
                expect="reject",
                rationale="additionalProperties=false but unexpected key present",
            )
        )

    return cases


def generate_surface_fuzz_cases(
    tools: dict[str, dict[str, Any]],
) -> list[FuzzCase]:
    """``tools`` maps tool name → inputSchema dict."""
    out: list[FuzzCase] = []
    for name, schema in sorted(tools.items()):
        out.extend(generate_fuzz_cases(name, schema or {}))
    return out
