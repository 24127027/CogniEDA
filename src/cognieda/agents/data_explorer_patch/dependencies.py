from pandas import DataFrame
from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class DataExplorerDeps:
    #TODO: Temporarily
    dataframe: DataFrame
    data_profile_id: UUID | None = None
    dataset_path: str | None = None