"""Deterministic canonicalization for scientific identity and digest boundaries."""

from __future__ import annotations

import json
from enum import Enum
from hashlib import sha256
from math import isfinite
from pathlib import PurePath
from typing import Any
from uuid import UUID

from pydantic import BaseModel


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize supported analytical values deterministically.

    Object keys are sorted by JSON, list order remains semantically significant,
    UUIDs/enums/paths are normalized, integral floats use their integer form, and
    non-finite numbers or unsupported objects are rejected.
    """

    normalized = _canonical_value(value)
    return json.dumps(
        normalized,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """Return the SHA-256 digest of canonical analytical content."""

    return sha256(canonical_json_bytes(value)).hexdigest()


def _canonical_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _canonical_value(value.model_dump(mode="python"))
    if isinstance(value, Enum):
        return _canonical_value(value.value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, PurePath):
        return value.as_posix()
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("Canonical JSON object keys must be strings.")
        return {key: _canonical_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("Canonical analytical content cannot contain NaN or Infinity.")
        if value == 0.0:
            return 0
        if value.is_integer():
            return int(value)
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"Unsupported canonical analytical value: {type(value).__name__}.")
