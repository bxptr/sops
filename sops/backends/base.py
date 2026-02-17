from __future__ import annotations

from typing import Any, Protocol


class Backend(Protocol):
    """Minimal backend contract for SOPS."""

    def infer_text(self, prompt: str) -> str:
        """Run a plain text model call and return text output."""

    def infer_json(self, prompt: str, schema_json: dict[str, Any], schema_name: str) -> Any:
        """Run a structured model call and return parsed JSON-like output."""
