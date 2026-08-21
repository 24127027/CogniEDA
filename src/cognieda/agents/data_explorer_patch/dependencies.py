from dataclasses import dataclass
from uuid import UUID

from pandas import DataFrame


@dataclass(frozen=True)
class DataExplorerDeps:
    dataframe: DataFrame
    data_profile_id: UUID | None = None
