"""Verify that a provider surface still satisfies consumer contracts."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .compat import is_type_compatible
from .consumer import ConsumerContract, Interaction
from .provider import ProviderSurface, ToolSurface


@dataclass
class InteractionFailure:
    consumer: str
    tool: str
    reason: str
    severity: str = "breaking"


@dataclass
class VerificationResult:
    consumer: str
    provider: str
    failures: list[InteractionFailure] = field(default_factory=list)
    checked_interactions: int = 0

    @property
    def ok(self) -> bool:
        return not any(f.severity == "breaking" for f in self.failures)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "consumer": self.consumer,
            "provider": self.provider,
            "checked_interactions": self.checked_interactions,
            "failures": [
                {
                    "consumer": f.consumer,
                    "tool": f.tool,
                    "reason": f.reason,
                    "severity": f.severity,
                }
                for f in self.failures
            ],
        }


def _infer_required(interaction: Interaction) -> list[str]:
    if interaction.required_arguments:
        return list(interaction.required_arguments)
    # Default: every key present in the example arguments is required by this call path
    return sorted(interaction.arguments.keys())


def _infer_arg_schema(interaction: Interaction, name: str, value: Any) -> dict[str, Any]:
    if name in interaction.argument_types:
        return interaction.argument_types[name]
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, list):
        return {"type": "array"}
    if isinstance(value, dict):
        return {"type": "object"}
    if value is None:
        return {"type": "null"}
    return {"type": "string"}


def verify_interaction(
    interaction: Interaction,
    tool: ToolSurface | None,
    *,
    consumer: str,
) -> list[InteractionFailure]:
    failures: list[InteractionFailure] = []
    if tool is None:
        failures.append(
            InteractionFailure(
                consumer=consumer,
                tool=interaction.tool,
                reason=f"Tool {interaction.tool!r} missing from provider",
            )
        )
        return failures

    required = _infer_required(interaction)
    provider_props = tool.properties
    provider_required = set(tool.required)

    for arg in required:
        if arg not in provider_props:
            failures.append(
                InteractionFailure(
                    consumer=consumer,
                    tool=interaction.tool,
                    reason=f"Consumer requires argument {arg!r} but provider schema has no such property",
                )
            )
            continue
        # If consumer sends it, provider must accept it — and if provider marks
        # other args required that consumer never sends, that also breaks.
        cons_schema = _infer_arg_schema(
            interaction, arg, interaction.arguments.get(arg)
        )
        prov_schema = provider_props.get(arg) if isinstance(provider_props.get(arg), dict) else {}
        if not is_type_compatible(prov_schema, cons_schema):
            failures.append(
                InteractionFailure(
                    consumer=consumer,
                    tool=interaction.tool,
                    reason=(
                        f"Provider type for {arg!r} is incompatible with consumer "
                        f"(provider={prov_schema.get('type')!r}, consumer sends {cons_schema.get('type')!r})"
                    ),
                )
            )

    # Provider-required args the consumer never supplies → broken call path
    consumer_keys = set(interaction.arguments) | set(required)
    for pref in sorted(provider_required - consumer_keys):
        failures.append(
            InteractionFailure(
                consumer=consumer,
                tool=interaction.tool,
                reason=(
                    f"Provider requires {pref!r} but consumer interaction never supplies it "
                    f"(call would fail)"
                ),
            )
        )
    return failures


def verify_consumer_against_provider(
    contract: ConsumerContract,
    provider: ProviderSurface,
) -> VerificationResult:
    result = VerificationResult(consumer=contract.consumer, provider=contract.provider)
    for interaction in contract.interactions:
        result.checked_interactions += 1
        tool = provider.get(interaction.tool)
        result.failures.extend(
            verify_interaction(interaction, tool, consumer=contract.consumer)
        )
    return result


@dataclass
class DeployDecision:
    ok: bool
    results: list[VerificationResult] = field(default_factory=list)

    @property
    def failures(self) -> list[InteractionFailure]:
        out: list[InteractionFailure] = []
        for r in self.results:
            out.extend(r.failures)
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "consumers_checked": len(self.results),
            "results": [r.to_dict() for r in self.results],
        }


def can_i_deploy(
    provider: ProviderSurface,
    contracts: Iterable[ConsumerContract],
) -> DeployDecision:
    """Return whether this provider surface satisfies every consumer contract."""
    results = [verify_consumer_against_provider(c, provider) for c in contracts]
    return DeployDecision(ok=all(r.ok for r in results), results=results)
