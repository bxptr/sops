from __future__ import annotations

import os
from typing import Any

from .backends.base import Backend
from .backends.openai_backend import OpenAIBackend
from .core import a as _a
from .core import c as _c
from .core import f as _f
from .core import o as _o
from .schema import SchemaSpec


def openai(*, model: str, api_key: str | None = None) -> OpenAIBackend:
    """Create an OpenAI backend instance."""
    return OpenAIBackend(model=model, api_key=api_key)


backend: Backend | None = openai(model=os.getenv("SOPS_MODEL", "gpt-5.2"))


def o(schema_dict: dict[str, object]) -> SchemaSpec:
    return _o(schema_dict)


def f(
    prompt: str,
    schema: SchemaSpec | None = None,
) -> str | dict[str, Any] | list[Any] | bool | int | float:
    return _f(prompt, schema=schema, backend=backend)


def c(prompt: str) -> bool:
    return _c(prompt, backend=backend)


def a(prompt: str, of: object) -> list[Any]:
    return _a(prompt, of=of, backend=backend)


__all__ = [
    "backend",
    "openai",
    "f",
    "o",
    "c",
    "a",
    "Backend",
    "OpenAIBackend",
    "SchemaSpec",
]
