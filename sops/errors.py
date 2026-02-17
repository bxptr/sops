from __future__ import annotations


class SopsError(Exception):
    """Base exception for all SOPS runtime errors."""


class ConfigurationError(SopsError):
    """Raised when SOPS is misconfigured (for example, backend not set)."""


class SchemaError(SopsError):
    """Raised when a schema cannot be compiled or is invalid."""


class ValidationError(SopsError):
    """Raised when model output does not match the provided schema."""


class BackendError(SopsError):
    """Raised when a backend call fails."""


class DecodeError(BackendError):
    """Raised when backend output cannot be decoded into expected format."""
