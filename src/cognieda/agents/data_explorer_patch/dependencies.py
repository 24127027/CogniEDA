
from pandas import DataFrame
from dataclasses import dataclass

@dataclass(frozen=True)
class DataExplorerDeps:
    #TODO: Temporarily
    dataframe: DataFrame