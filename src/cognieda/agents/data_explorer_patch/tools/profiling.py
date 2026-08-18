from pydantic_ai import RuntimeContext

from cognieda.schemas.artifacts import DataProfile
from cognieda.schemas.common import ColumnProfile
from cognieda.schemas.enums import VariableType

from ..dependencies import DataExplorerDeps

from cognieda.agents.utilities import function_registry

dataset_profiling = function_registry.FunctionRegistry()


@dataset_profiling.register
def profiling(ctx: RuntimeContext[DataExplorerDeps]) -> DataProfile:
    """Create a deterministic structural profile of the active dataframe."""
    dataframe = ctx.deps.dataframe

    columns = tuple(
        ColumnProfile(
            name=str(column),
            dtype=str(dataframe[column].dtype),
            variable_type=(
                VariableType.CONTINUOUS
                if dataframe[column].dtype.kind in "iufc"
                else VariableType.DISCRETE
            ),
            distinct_count=int(dataframe[column].nunique(dropna=True)),
            missing_count=int(dataframe[column].isna().sum()),
        )
        for column in dataframe.columns
    )

    return DataProfile(
        row_count=len(dataframe),
        column_count=len(dataframe.columns),
        columns=columns,
    )

__all__ = [
    "dataset_profiling",
]