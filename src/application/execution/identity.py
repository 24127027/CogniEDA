"""Authority-neutral canonicalization for execution contracts and receipts."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

from pydantic import BaseModel

from schemas.canonical import canonical_json_bytes, canonical_sha256

__all__ = [
    "canonical_json_bytes",
    "canonical_sha256",
    "method_parameter_hash",
    "result_payload_digest",
]


def result_payload_digest(payload: dict[str, Any]) -> str:
    """Preserve the receiver's exact canonical digest for a JSON-safe result payload."""

    canonical = json.dumps(
        payload,
        sort_keys=True,
        allow_nan=False,
        separators=(",", ":"),
    )
    return sha256(canonical.encode()).hexdigest()


def method_parameter_hash(parameters: list[Any]) -> str:
    """Preserve the legacy method-parameter hash outside scientific authority modules."""

    payload = [
        parameter.model_dump(mode="json") if isinstance(parameter, BaseModel) else parameter
        for parameter in parameters
    ]
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
