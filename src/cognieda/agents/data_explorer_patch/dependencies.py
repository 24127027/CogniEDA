from pandas import DataFrame
from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class DataExplorerDeps:
    #TODO: Temporarily
    dataframe: DataFrame
