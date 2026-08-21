from unittest.mock import MagicMock

import pandas as pd

from cognieda.agents.data_explorer_patch.dependencies import DataExplorerDeps
from cognieda.agents.data_explorer_patch.tools.profiling import profiling
from cognieda.schemas.artifacts import DataProfile
from cognieda.schemas.enums import VariableType


def test_profiling():
    df = pd.DataFrame({"A": [1, 2, 3], "B": ["x", "y", "z"]})
    deps = DataExplorerDeps(dataframe=df)
    ctx = MagicMock()
    ctx.deps = deps
    
    result = profiling(ctx)
    
    assert isinstance(result, DataProfile)
    assert result.row_count == 3
    assert result.column_count == 2
    assert len(result.columns) == 2
    assert result.columns[0].name == "A"
    assert result.columns[0].variable_type == VariableType.CONTINUOUS
    assert result.columns[1].name == "B"
    assert result.columns[1].variable_type == VariableType.DISCRETE
