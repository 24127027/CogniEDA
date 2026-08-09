from __future__ import annotations

from typing import Any

import pandas as pd


def run_unsafe_python_analysis(code: str, dataframe: pd.DataFrame) -> Any:
    """Run provisional generated analysis code without a security boundary.

    This adapter preserves the current donor behavior while making its unsafe
    execution authority explicit. It is not a production sandbox and must not
    be exposed as a general-purpose executor.
    """
    namespace: dict[str, Any] = {
        "dataframe": dataframe,
        "pd": pd,
        "result": None,
    }
    exec(compile(code, "<data_explorer>", "exec"), namespace, namespace)
    return namespace.get("result")
