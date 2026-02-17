from __future__ import annotations

import json
import os
from typing import Any

from ..errors import BackendError, DecodeError

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - exercised in runtime if dependency missing.
    OpenAI = None  # type: ignore[assignment]


class OpenAIBackend:
    """OpenAI Responses API backend for SOPS."""

    def __init__(self, *, model: str, api_key: str | None = None) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model must be a non-empty string.")
        self.model = model
        self.api_key = api_key

        if OpenAI is None:
            raise BackendError("openai package is required to use OpenAIBackend.")
        self._client: Any | None = None

    def infer_text(self, prompt: str) -> str:
        client = self._get_client()
        try:
            response = client.responses.create(model=self.model, input=prompt)
        except Exception as exc:  # pragma: no cover - backend call failures are environment-specific.
            raise BackendError("OpenAI text request failed.") from exc

        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str):
            raise DecodeError("OpenAI response did not include string output_text.")
        return output_text

    def infer_json(self, prompt: str, schema_json: dict[str, Any], schema_name: str) -> Any:
        client = self._get_client()
        payload = {
            "type": "json_schema",
            "name": schema_name,
            "schema": schema_json,
            "strict": True,
        }
        try:
            response = client.responses.create(
                model=self.model,
                input=prompt,
                text={"format": payload},
            )
        except Exception as exc:  # pragma: no cover - backend call failures are environment-specific.
            raise BackendError("OpenAI structured request failed.") from exc

        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str):
            raise DecodeError("OpenAI structured response did not include string output_text.")

        try:
            return json.loads(output_text)
        except Exception as exc:
            raise DecodeError("Failed to decode OpenAI structured output as JSON.") from exc

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        resolved_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise BackendError(
                "Missing OpenAI API key. Pass api_key to sops.openai(...) or set OPENAI_API_KEY."
            )

        self._client = OpenAI(api_key=resolved_key)
        return self._client
