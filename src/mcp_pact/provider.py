"""Normalize an MCP provider tool surface (from tools/list or a snapshot file)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ToolSurface:
    name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)

    @property
    def properties(self) -> dict[str, Any]:
        props = self.input_schema.get("properties") or {}
        return props if isinstance(props, dict) else {}

    @property
    def required(self) -> list[str]:
        req = self.input_schema.get("required") or []
        return [str(x) for x in req] if isinstance(req, list) else []

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


@dataclass
class ProviderSurface:
    server_name: str
    tools: dict[str, ToolSurface]
    metadata: dict[str, Any] = field(default_factory=dict)

    def get(self, name: str) -> ToolSurface | None:
        return self.tools.get(name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "server_name": self.server_name,
            "metadata": self.metadata,
            "tools": {k: v.to_dict() for k, v in sorted(self.tools.items())},
        }

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n")


def _tool_from_raw(raw: dict[str, Any]) -> ToolSurface:
    name = raw.get("name")
    if not name:
        raise ValueError("Tool entry missing name")
    schema = raw.get("inputSchema") or raw.get("input_schema") or {}
    if not isinstance(schema, dict):
        schema = {}
    return ToolSurface(
        name=str(name),
        description=str(raw.get("description") or ""),
        input_schema=schema,
    )


def provider_surface_from_tools_list(
    tools: list[dict[str, Any]],
    *,
    server_name: str = "mcp-server",
    metadata: dict[str, Any] | None = None,
) -> ProviderSurface:
    """Build a surface from an MCP ``tools/list`` result (list of tool dicts)."""
    mapped = {_tool_from_raw(t).name: _tool_from_raw(t) for t in tools}
    return ProviderSurface(
        server_name=server_name,
        tools=mapped,
        metadata=metadata or {},
    )


def load_provider_surface(path: str | Path) -> ProviderSurface:
    """Load a provider surface from a JSON snapshot (dict or tools/list array)."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Provider surface not found: {path}")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Provider surface {path} is not valid JSON: {exc}") from exc
    if "tools" not in data:
        # Allow raw tools/list array or {"tools": [...]}
        if isinstance(data, list):
            return provider_surface_from_tools_list(data)
        raise ValueError(
            f"Provider surface {path} must contain a 'tools' object or be a tools/list array"
        )

    tools_node = data["tools"]
    if isinstance(tools_node, list):
        return provider_surface_from_tools_list(
            tools_node,
            server_name=str(data.get("server_name") or "mcp-server"),
            metadata=data.get("metadata") or {},
        )
    if isinstance(tools_node, dict):
        tools = {
            name: _tool_from_raw({**raw, "name": raw.get("name", name)})
            for name, raw in tools_node.items()
        }
        return ProviderSurface(
            server_name=str(data.get("server_name") or "mcp-server"),
            tools=tools,
            metadata=data.get("metadata") or {},
        )
    raise ValueError(
        f"Unsupported tools format in provider surface {path}: "
        f"expected object or list, got {type(tools_node).__name__}"
    )
