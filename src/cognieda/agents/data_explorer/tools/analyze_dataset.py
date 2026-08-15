"""Deterministic allowlisted analytical tools for the M3-A Evidence path."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from pydantic import JsonValue


TOOL_VERSION = "v1"


class DataToolError(ValueError):
    """Expected deterministic tool rejection with a stable failure code."""

    code = "tool_execution_error"


class ColumnNotFoundError(DataToolError):
    code = "column_not_found"


class InvalidAnalysisPlanError(DataToolError):
    code = "invalid_analysis_plan"


class InvalidToolResultError(DataToolError):
    code = "invalid_result"


def tool_reference(operation_value: str) -> str:
    return f"cognieda.data_explorer.{operation_value}:{TOOL_VERSION}"


def normalize_json_value(value: Any) -> JsonValue:
    """Normalize supported scalar containers and reject opaque runtime objects."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, np.generic):
        return normalize_json_value(value.item())
    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidToolResultError("Tool output contains a non-finite float.")
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Mapping):
        normalized: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise InvalidToolResultError("Tool output requires string object keys.")
            normalized[key] = normalize_json_value(item)
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [normalize_json_value(item) for item in value]
    raise InvalidToolResultError(
        f"Tool output contains unsupported value type {type(value).__name__}."
    )


def parse_string_list(value: str) -> list[str]:
    """Robustly parse a string representation of a list of columns.
    
    Handles formats like:
      - "['price', 'stock']"
      - "price, stock"
      - "'price', 'stock'"
    """
    import ast
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, (list, tuple)):
            return [str(c) for c in parsed]
    except (SyntaxError, ValueError):
        pass
        
    return [c.strip("[]'\" ") for c in value.split(",") if c.strip("[]'\" ")]
