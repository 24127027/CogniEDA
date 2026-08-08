from enum import StrEnum


class Capability(StrEnum):
    DATA_ANALYSIS = "data_analysis"
    DATA_PROFILING = "data_profiling"
    DATA_TRANSFORMATION = "data_transformation"

    GRAPH_MINING = "graph_mining"
    HYPOTHESIS_TESTING = "hypothesis_testing"