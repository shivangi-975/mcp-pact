"""Provider surface diffs + consumer-impact analysis."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .compat import Change, CompatibilityReport, classify_schema_change
from .consumer import ConsumerContract
from .provider import ProviderSurface
from .verify import VerificationResult, verify_consumer_against_provider


@dataclass
class SurfaceDiff:
    report: CompatibilityReport = field(default_factory=CompatibilityReport)
    removed_tools: list[str] = field(default_factory=list)
    added_tools: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.report.ok

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "removed_tools": self.removed_tools,
            "added_tools": self.added_tools,
            **self.report.to_dict(),
        }


def diff_provider_surfaces(old: ProviderSurface, new: ProviderSurface) -> SurfaceDiff:
    result = SurfaceDiff()
    old_names, new_names = set(old.tools), set(new.tools)
    result.removed_tools = sorted(old_names - new_names)
    result.added_tools = sorted(new_names - old_names)

    for name in result.removed_tools:
        result.report.changes.append(
            Change(name, "breaking", f"Tool {name!r} removed")
        )
    for name in result.added_tools:
        result.report.changes.append(
            Change(name, "additive", f"Tool {name!r} added")
        )

    for name in sorted(old_names & new_names):
        o, n = old.tools[name], new.tools[name]
        sub = classify_schema_change(
            old_required=o.required,
            new_required=n.required,
            old_props=o.properties,
            new_props=n.properties,
            old_description=o.description,
            new_description=n.description,
            tool_name=name,
        )
        result.report.changes.extend(sub.changes)
    return result


@dataclass
class ImpactReport:
    surface_diff: SurfaceDiff
    consumer_results: list[VerificationResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.surface_diff.ok and all(r.ok for r in self.consumer_results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "surface_diff": self.surface_diff.to_dict(),
            "consumer_results": [r.to_dict() for r in self.consumer_results],
        }


def impact_of_provider_change(
    old: ProviderSurface,
    new: ProviderSurface,
    consumers: Iterable[ConsumerContract],
) -> ImpactReport:
    """Schema diff PLUS re-verify every consumer against the *new* surface."""
    surface = diff_provider_surfaces(old, new)
    results = [verify_consumer_against_provider(c, new) for c in consumers]
    return ImpactReport(surface_diff=surface, consumer_results=results)
