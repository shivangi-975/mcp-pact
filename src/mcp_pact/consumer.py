"""Consumer (agent) contracts — what an agent actually needs from an MCP server."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Interaction:
    """One expected tool usage by the consumer."""

    tool: str
    description: str = ""
    # Arguments the consumer will send (example / fixture)
    arguments: dict[str, Any] = field(default_factory=dict)
    # Optional: JSON Schema fragments the consumer relies on for each arg
    argument_types: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Arguments the consumer treats as required for its call path
    required_arguments: list[str] = field(default_factory=list)
    # Optional expected output shape (JSON Schema) — structural only
    expect_output_schema: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Interaction:
        return cls(
            tool=str(data["tool"]),
            description=str(data.get("description") or ""),
            arguments=dict(data.get("arguments") or {}),
            argument_types={
                k: v for k, v in (data.get("argument_types") or {}).items() if isinstance(v, dict)
            },
            required_arguments=list(data.get("required_arguments") or data.get("requires") or []),
            expect_output_schema=data.get("expect_output_schema"),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"tool": self.tool}
        if self.description:
            out["description"] = self.description
        if self.arguments:
            out["arguments"] = self.arguments
        if self.argument_types:
            out["argument_types"] = self.argument_types
        if self.required_arguments:
            out["required_arguments"] = self.required_arguments
        if self.expect_output_schema is not None:
            out["expect_output_schema"] = self.expect_output_schema
        return out


@dataclass
class ConsumerContract:
    """Pact-style contract: consumer name + interactions against a provider."""

    consumer: str
    provider: str
    interactions: list[Interaction]
    version: str = "1"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "consumer": self.consumer,
            "provider": self.provider,
            "version": self.version,
            "metadata": self.metadata,
            "interactions": [i.to_dict() for i in self.interactions],
        }

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        text = yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True)
        path.write_text(text)


def load_consumer_contract(path: str | Path) -> ConsumerContract:
    """Load a consumer contract from a YAML or JSON file."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Consumer contract not found: {path}")
    raw = path.read_text()
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(raw)
    else:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Consumer contract {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise TypeError(f"Consumer contract {path} must be a mapping, got {type(data).__name__}")
    interactions = [
        Interaction.from_dict(i) for i in (data.get("interactions") or []) if isinstance(i, dict)
    ]
    if not data.get("consumer") or not data.get("provider"):
        raise ValueError(
            f"Consumer contract {path} requires non-empty 'consumer' and 'provider' fields"
        )
    return ConsumerContract(
        consumer=str(data["consumer"]),
        provider=str(data["provider"]),
        interactions=interactions,
        version=str(data.get("version") or "1"),
        metadata=dict(data.get("metadata") or {}),
    )
