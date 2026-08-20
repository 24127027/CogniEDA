from unittest.mock import MagicMock
from uuid import uuid4

import pandas as pd
import pytest

from cognieda.agents.data_explorer_patch.dependencies import DataExplorerDeps
from cognieda.agents.data_explorer_patch.tools.sandbox import execute_code


@pytest.fixture
def mock_ctx():
    df = pd.DataFrame({"A": [1, 2, 3]})
    deps = DataExplorerDeps(dataframe=df, data_profile_id=uuid4())
    ctx = MagicMock()
    ctx.deps = deps
    return ctx

def test_execute_code_success(mock_ctx):
    code = "result = df['A'].sum()"
    res = execute_code(mock_ctx, code=code)
    assert "error" not in res
    assert res["output"]["value"] == 6

def test_execute_code_missing_result(mock_ctx):
    code = "x = df['A'].sum()"
    res = execute_code(mock_ctx, code=code)
    assert res["error"] == "missing_result"

def test_execute_code_security(mock_ctx):
    code = "import os\nresult = os.getcwd()"
    res = execute_code(mock_ctx, code=code)
    assert res["error"] == "security"

