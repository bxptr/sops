from __future__ import annotations

import types
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal, Union, get_args, get_origin

from .errors import SchemaError, ValidationError

_NONE_TYPE = type(None)


@dataclass(frozen=True)
class SchemaSpec:
    """Compiled schema wrapper consumed by sops.f()."""

    schema_dict: dict[str, object]
    json_schema: dict[str, Any]
    name: str = "sops_output"


def make_schema_spec(schema_dict: dict[str, object]) -> SchemaSpec:
    if not isinstance(schema_dict, dict):
        raise SchemaError("sops.o(...) expects a Python dict schema at the root.")
    _ensure_string_keys(schema_dict, path=())
    compiled = _compile_object_schema(schema_dict, path=())
    return SchemaSpec(schema_dict=deepcopy(schema_dict), json_schema=compiled)


def validate_with_schema_dict(value: object, schema_dict: dict[str, object]) -> None:
    _validate_object(value, schema_dict, path=())


def _ensure_string_keys(schema_dict: dict[str, object], path: tuple[object, ...]) -> None:
    for key, sub_schema in schema_dict.items():
        if not isinstance(key, str):
            raise SchemaError(f"Object schema keys must be strings at {_path_str(path)}.")
        if isinstance(sub_schema, dict):
            _ensure_string_keys(sub_schema, path=(*path, key))


def _compile_object_schema(schema_dict: dict[str, object], path: tuple[object, ...]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []

    for key, field_schema in schema_dict.items():
        compiled_field, _optional = _compile_field_schema(field_schema, path=(*path, key))
        properties[key] = compiled_field
        # OpenAI strict structured outputs require every property key to be listed in
        # "required". Optionality is represented via nullable field schemas.
        required.append(key)

    result: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        result["required"] = required
    return result


def _compile_field_schema(schema: object, path: tuple[object, ...]) -> tuple[dict[str, Any], bool]:
    inner_schema, optional = _unwrap_optional(schema, path=path)
    compiled = _compile_any_schema(inner_schema, path=path)
    if optional:
        return {"anyOf": [compiled, {"type": "null"}]}, True
    return compiled, False


def _compile_any_schema(schema: object, path: tuple[object, ...]) -> dict[str, Any]:
    if isinstance(schema, dict):
        _ensure_string_keys(schema, path=path)
        return _compile_object_schema(schema, path=path)

    if isinstance(schema, list):
        if len(schema) != 1:
            raise SchemaError(
                f"List schema shorthand must contain exactly one item type at {_path_str(path)}."
            )
        return {"type": "array", "items": _compile_any_schema(schema[0], path=(*path, "[]"))}

    origin = get_origin(schema)
    if origin in (list,):
        args = get_args(schema)
        if len(args) != 1:
            raise SchemaError(f"list[T] requires exactly one item type at {_path_str(path)}.")
        return {"type": "array", "items": _compile_any_schema(args[0], path=(*path, "[]"))}

    if origin is Literal:
        values = list(get_args(schema))
        if not values:
            raise SchemaError(f"Literal must include at least one value at {_path_str(path)}.")
        for value in values:
            if value is not None and not isinstance(value, (str, int, float, bool)):
                raise SchemaError(
                    f"Unsupported Literal value {value!r} at {_path_str(path)}. "
                    "Use str, int, float, bool, or None."
                )
        return {"enum": values}

    if schema is str:
        return {"type": "string"}
    if schema is int:
        return {"type": "integer"}
    if schema is float:
        return {"type": "number"}
    if schema is bool:
        return {"type": "boolean"}

    if origin in (Union, types.UnionType):
        raise SchemaError(
            f"Only Optional[T] unions are supported at {_path_str(path)}; "
            f"received {schema!r}."
        )

    raise SchemaError(f"Unsupported schema type {schema!r} at {_path_str(path)}.")


def _unwrap_optional(schema: object, path: tuple[object, ...]) -> tuple[object, bool]:
    origin = get_origin(schema)
    if origin not in (Union, types.UnionType):
        return schema, False

    args = get_args(schema)
    non_none = [arg for arg in args if arg is not _NONE_TYPE]
    has_none = len(non_none) != len(args)
    if not has_none:
        return schema, False
    if len(non_none) != 1:
        raise SchemaError(
            f"Only Optional[T] unions are supported at {_path_str(path)}; "
            f"received {schema!r}."
        )
    return non_none[0], True


def _validate_object(value: object, schema_dict: dict[str, object], path: tuple[object, ...]) -> None:
    if not isinstance(value, dict):
        raise ValidationError(
            f"Expected object at {_path_str(path)}, got {type(value).__name__}."
        )

    extra_keys = set(value.keys()) - set(schema_dict.keys())
    if extra_keys:
        raise ValidationError(
            f"Unexpected field(s) {sorted(extra_keys)!r} at {_path_str(path)}."
        )

    for key, field_schema in schema_dict.items():
        inner_schema, optional = _unwrap_optional(field_schema, path=(*path, key))
        if key not in value:
            if optional:
                continue
            raise ValidationError(f"Missing required field '{key}' at {_path_str(path)}.")

        field_value = value[key]
        if field_value is None:
            if optional:
                continue
            raise ValidationError(f"Field '{key}' cannot be null at {_path_str((*path, key))}.")
        _validate_any(field_value, inner_schema if optional else field_schema, path=(*path, key))


def _validate_any(value: object, schema: object, path: tuple[object, ...]) -> None:
    if isinstance(schema, dict):
        _validate_object(value, schema, path=path)
        return

    if isinstance(schema, list):
        if len(schema) != 1:
            raise SchemaError(
                f"List schema shorthand must contain exactly one item type at {_path_str(path)}."
            )
        if not isinstance(value, list):
            raise ValidationError(
                f"Expected list at {_path_str(path)}, got {type(value).__name__}."
            )
        for index, item in enumerate(value):
            _validate_any(item, schema[0], path=(*path, index))
        return

    inner_schema, optional = _unwrap_optional(schema, path=path)
    if optional:
        if value is None:
            return
        _validate_any(value, inner_schema, path=path)
        return

    origin = get_origin(schema)
    if origin in (list,):
        args = get_args(schema)
        if len(args) != 1:
            raise SchemaError(f"list[T] requires exactly one item type at {_path_str(path)}.")
        if not isinstance(value, list):
            raise ValidationError(
                f"Expected list at {_path_str(path)}, got {type(value).__name__}."
            )
        for index, item in enumerate(value):
            _validate_any(item, args[0], path=(*path, index))
        return

    if origin is Literal:
        allowed_values = get_args(schema)
        if value not in allowed_values:
            raise ValidationError(
                f"Value {value!r} at {_path_str(path)} is not in Literal{allowed_values!r}."
            )
        return

    if schema is str:
        if not isinstance(value, str):
            raise ValidationError(
                f"Expected string at {_path_str(path)}, got {type(value).__name__}."
            )
        return

    if schema is bool:
        if not isinstance(value, bool):
            raise ValidationError(
                f"Expected boolean at {_path_str(path)}, got {type(value).__name__}."
            )
        return

    if schema is int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValidationError(
                f"Expected integer at {_path_str(path)}, got {type(value).__name__}."
            )
        return

    if schema is float:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValidationError(
                f"Expected number at {_path_str(path)}, got {type(value).__name__}."
            )
        return

    raise SchemaError(f"Unsupported schema type {schema!r} at {_path_str(path)}.")


def _path_str(path: tuple[object, ...]) -> str:
    if not path:
        return "$"

    rendered = "$"
    for part in path:
        if isinstance(part, int):
            rendered += f"[{part}]"
        elif part == "[]":
            rendered += "[]"
        else:
            rendered += f".{part}"
    return rendered
