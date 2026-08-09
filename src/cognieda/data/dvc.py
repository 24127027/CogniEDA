"""DVC integration boundary for DataProfile creation."""

from __future__ import annotations

from dataclasses import dataclass


class DvcIntegrationNotImplementedError(NotImplementedError):
    """Raised when executable DVC integration is requested before it exists."""


@dataclass(frozen=True, slots=True)
class DvcDatasetIdentity:
    """Version identity captured from DVC or an equivalent data-versioning layer."""

    dvc_hash: str
    dvc_version_label: str | None = None


class DvcAdapter:
    """Interface for resolving dataset-version identity for a path."""

    def resolve_dataset_identity(self, dataset_path: str) -> DvcDatasetIdentity:
        """Return DVC identity for a dataset path.

        The current repository declares the boundary but does not execute DVC.
        Implementations should shell out to DVC or read DVC metadata in a later
        integration patch.
        """

        raise DvcIntegrationNotImplementedError(
            f"DVC identity resolution is not implemented for {dataset_path!r}."
        )
