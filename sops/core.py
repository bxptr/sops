from __future__ import annotations

from typing import Any

from .backends.base import Backend
from .errors import ConfigurationError, SchemaError, ValidationError
from .schema import SchemaSpec, make_schema_spec, validate_with_schema_dict


def o(schema_dict: dict[str, object]) -> SchemaSpec:
    """Build a structured schema spec for use with sops.f()."""
    return make_schema_spec(schema_dict)


def f(
    prompt: str,
    schema: SchemaSpec | None = None,
    *,
    backend: Backend | None,
) -> str | dict[str, Any] | list[Any] | bool | int | float:
    """Primary SOPS call: plain text or structured output."""
    if not isinstance(prompt, str):
        raise TypeError("sops.f(prompt, ...) expects prompt to be a string.")

    if isinstance(schema, dict):
        raise SchemaError("Pass schema as sops.o({...}), not a raw dict.")
    if schema is not None and not isinstance(schema, SchemaSpec):
        raise SchemaError("schema must be None or a SchemaSpec created by sops.o({...}).")

    resolved_backend = _require_backend(backend)
    if schema is None:
        return resolved_backend.infer_text(prompt)

    value = resolved_backend.infer_json(prompt, schema.json_schema, schema.name)
    validate_with_schema_dict(value, schema.schema_dict)
    return value


def c(prompt: str, *, backend: Backend | None) -> bool:
    """Boolean helper backed by structured output."""
    result = f(prompt, o({"result": bool}), backend=backend)
    if not isinstance(result, dict) or "result" not in result:
        raise ValidationError("Expected {'result': bool} output shape from sops.c().")
    value = result["result"]
    if not isinstance(value, bool):
        raise ValidationError("Expected boolean value for key 'result' in sops.c().")
    return value


def a(prompt: str, of: object, *, backend: Backend | None) -> list[Any]:
    """Array helper backed by structured output."""
    result = f(prompt, o({"items": [of]}), backend=backend)
    if not isinstance(result, dict) or "items" not in result:
        raise ValidationError("Expected {'items': list} output shape from sops.a().")
    items = result["items"]
    if not isinstance(items, list):
        raise ValidationError("Expected list value for key 'items' in sops.a().")
    return items


def _require_backend(backend: Backend | None) -> Backend:
    if backend is None:
        raise ConfigurationError(
            "sops.backend is not set. Configure one first, e.g. "
            "sops.backend = sops.openai(model='gpt-5.2')."
        )
    return backend
