"""Redaction helpers for the dev-only request/response body dump.

Live in their own module so they're easy to unit-test and to extend with
new field names without touching middleware code.

Two layers of secrets we care about:

1. **Headers** — `Authorization`, `Cookie`, etc. carry tokens directly. We
   match on a fixed case-insensitive set.
2. **JSON-body fields** — credentials posted to login/register, JWT pairs
   in auth responses, future API keys. We match on a substring set
   (`password`, `token`, `secret`, `api_key`) so any field whose name
   contains one of those words gets redacted, on any depth.

Anything we don't recognise is passed through unchanged.
"""

from __future__ import annotations

from typing import Any

REDACTED = "***"

# Lowercased exact header names. Replaced wholesale.
SENSITIVE_HEADERS: frozenset[str] = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-auth-token",
    }
)

# Lowercased substrings. A JSON key whose name contains any of these gets
# its value masked. Substring match keeps the list short and survives
# minor naming variations (`password1`, `new_password`, `access_token`).
SENSITIVE_FIELD_SUBSTRINGS: tuple[str, ...] = (
    "password",
    "token",
    "secret",
    "api_key",
    "apikey",
    "access",
    "refresh",
)


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return a copy of `headers` with sensitive values replaced by ``***``."""
    return {
        name: (REDACTED if name.lower() in SENSITIVE_HEADERS else value)
        for name, value in headers.items()
    }


def redact_body(value: Any) -> Any:
    """Recursively walk a JSON-decoded value and mask sensitive leaves.

    Lists are traversed element-wise; dicts are traversed key-wise with the
    sensitive-name check applied to the key. Non-container values are
    returned unchanged. The function never mutates its input.
    """
    if isinstance(value, dict):
        return {
            key: (REDACTED if _is_sensitive_field(key) else redact_body(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_body(item) for item in value]
    return value


def _is_sensitive_field(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in SENSITIVE_FIELD_SUBSTRINGS)
