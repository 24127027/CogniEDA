from typing import Protocol

"""
    This module defines protocols for dependencies that can be used in tools
    Agents can declare it own dependencies by using these protocols
    Agent's dependencies are required to contain protocols that are used by the tools it uses,
      so that the agent can be properly initialized with the required dependencies.

"""


class HasGraphRepository(Protocol):
    """
        Dummy dependencies protocols for testing purposes.
    """
    ...

class HasDatasetRepository(Protocol):
    """
        Dummy dependencies protocols for testing purposes.
    """
    ...