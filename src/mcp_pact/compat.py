"""JSON Schema compatibility from the *consumer* (caller) point of view."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["breaking", "additive", "routing", "none"]


def _norm_types(schema: dict[str, Any] | None) -> set[str]:
    if not schema:
        return {"any"}
    t = schema.get("type")
    if t is None:
        if "anyOf" in schema or "oneOf" in schema:
            types: set[str] = set()
            for branch in schema.get("anyOf") or schema.get("oneOf") or []:
                types |= _norm_types(branch if isinstance(branch, dict) else {})
            return types or {"any"}
        return {"any"}
    if isinstance(t, list):
        return {str(x) for x in t}
    return {str(t)}


def is_type_compatible(provider_schema: dict[str, Any] | None, consumer_schema: dict[str, Any] | None) -> bool:
    """True if a provider input type can accept what the consumer will send.

    Consumer declares the type it *sends*. Provider must accept at least that
    (provider may be wider). Provider narrowing breaks the consumer.
    """
    prov = _norm_types(provider_schema)
    cons = _norm_types(consumer_schema)
    if "any" in prov or "any" in cons:
        return True
    # Provider must accept every type the consumer might send
    return cons.issubset(prov)


def classify_input_change(
    old: dict[str, Any] | None,
    new: dict[str, Any] | None,
) -> Severity:
    """Classify provider input schema evolution (old → new)."""
    if old == new:
        return "none"
    old_t, new_t = _norm_types(old), _norm_types(new)
    if old_t == new_t:
        return "none"
    # widening provider input = additive/safe; narrowing = breaking
    if old_t.issubset(new_t):
        return "additive"
    if new_t.issubset(old_t) and new_t != old_t:
        return "breaking"
    if old_t & new_t:
        return "breaking"  # partial overlap still risky
    return "breaking"


@dataclass
class Change:
    path: str
    severity: Severity
    message: str


@dataclass
class CompatibilityReport:
    changes: list[Change] = field(default_factory=list)

    @property
    def breaking(self) -> list[Change]:
        return [c for c in self.changes if c.severity == "breaking"]

    @property
    def ok(self) -> bool:
        return not self.breaking

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "changes": [
                {"path": c.path, "severity": c.severity, "message": c.message}
                for c in self.changes
            ],
        }


def classify_schema_change(
    *,
    old_required: list[str],
    new_required: list[str],
    old_props: dict[str, Any],
    new_props: dict[str, Any],
    old_description: str | None = None,
    new_description: str | None = None,
    tool_name: str = "tool",
) -> CompatibilityReport:
    """Diff two tool input schemas; severities are caller-centric."""
    report = CompatibilityReport()
    old_req, new_req = set(old_required), set(new_required)
    old_keys, new_keys = set(old_props), set(new_props)

    for removed in sorted(old_keys - new_keys):
        report.changes.append(
            Change(
                f"{tool_name}.input.{removed}",
                "breaking",
                f"Argument {removed!r} removed",
            )
        )
    for added in sorted(new_keys - old_keys):
        sev: Severity = "breaking" if added in new_req else "additive"
        msg = (
            f"Required argument {added!r} added"
            if sev == "breaking"
            else f"Optional argument {added!r} added"
        )
        report.changes.append(Change(f"{tool_name}.input.{added}", sev, msg))

    for name in sorted(old_req - new_req):
        if name in new_keys:
            report.changes.append(
                Change(
                    f"{tool_name}.input.{name}",
                    "additive",
                    f"Argument {name!r} no longer required",
                )
            )
    for name in sorted(new_req - old_req):
        if name in old_keys:
            report.changes.append(
                Change(
                    f"{tool_name}.input.{name}",
                    "breaking",
                    f"Argument {name!r} became required",
                )
            )

    for name in sorted(old_keys & new_keys):
        sev = classify_input_change(
            old_props.get(name) if isinstance(old_props.get(name), dict) else {},
            new_props.get(name) if isinstance(new_props.get(name), dict) else {},
        )
        if sev not in {"none", None}:
            report.changes.append(
                Change(
                    f"{tool_name}.input.{name}.type",
                    sev,
                    f"Type change on {name!r} ({sev})",
                )
            )

    if (
        (old_description or "").strip() != (new_description or "").strip()
        and (old_description is not None or new_description is not None)
    ):
        report.changes.append(
            Change(
                f"{tool_name}.description",
                "routing",
                "Tool description changed (may alter agent tool selection)",
            )
        )
    return report
