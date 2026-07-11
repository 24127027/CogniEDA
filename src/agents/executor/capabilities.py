from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilitySpec:
    id: str
    description: str


class Capability:
    DATA_EXPLORATION = CapabilitySpec(
        id="data_exploration",
        description=(
            "Inspect datasets, distributions, anomalies, representations, "
            "and statistical properties."
        ),
    )
    GRAPH_MINING = CapabilitySpec(
        id="graph_mining",
        description=(
            "Discover relationships and structural patterns in the knowledge graph."
        ),
    )
    HYPOTHESIS_TESTING = CapabilitySpec(
        id="hypothesis_testing",
        description="Formulate and evaluate testable scientific hypotheses.",
    )


PLANNER_CAPABILITIES = (
    Capability.DATA_EXPLORATION,
    Capability.GRAPH_MINING,
    Capability.HYPOTHESIS_TESTING,
)

ALL_CAPABILITIES = PLANNER_CAPABILITIES

CAPABILITY_IDS = tuple(capability.id for capability in ALL_CAPABILITIES)
