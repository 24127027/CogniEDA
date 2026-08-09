"""Deterministic dataset loaders for local profiling workflows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import pandas as pd


class SupportedDatasetFormat(StrEnum):
    """File formats supported by the initial local data core."""

    CSV = "csv"
    PARQUET = "parquet"


@dataclass(frozen=True, slots=True)
class LoadedDataset:
    """Loaded dataset payload with normalized path metadata."""

    path: Path
    dataset_format: SupportedDatasetFormat
    dataframe: pd.DataFrame


def _resolve_dataset_path(path: str | Path) -> Path:
    resolved_path = Path(path).expanduser().resolve()
    if not resolved_path.exists():
        raise FileNotFoundError(f"Dataset path does not exist: {resolved_path}")
    if not resolved_path.is_file():
        raise ValueError(f"Dataset path is not a file: {resolved_path}")
    return resolved_path


def _detect_dataset_format(path: Path) -> SupportedDatasetFormat:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return SupportedDatasetFormat.CSV
    if suffix in {".parquet", ".pq"}:
        return SupportedDatasetFormat.PARQUET
    raise ValueError(f"Unsupported dataset format for path: {path}")


def load_csv_dataset(path: str | Path) -> LoadedDataset:
    """Load a CSV dataset into a deterministic DataFrame wrapper."""

    resolved_path = _resolve_dataset_path(path)
    dataframe = pd.read_csv(resolved_path)
    return LoadedDataset(
        path=resolved_path,
        dataset_format=SupportedDatasetFormat.CSV,
        dataframe=dataframe,
    )


def load_parquet_dataset(path: str | Path) -> LoadedDataset:
    """Load a Parquet dataset into a deterministic DataFrame wrapper."""

    resolved_path = _resolve_dataset_path(path)
    dataframe = pd.read_parquet(resolved_path)
    return LoadedDataset(
        path=resolved_path, dataset_format=SupportedDatasetFormat.PARQUET, dataframe=dataframe
    )


def load_dataset(path: str | Path) -> LoadedDataset:
    """Load a dataset by inferring support from the file extension."""

    resolved_path = _resolve_dataset_path(path)
    dataset_format = _detect_dataset_format(resolved_path)
    if dataset_format is SupportedDatasetFormat.CSV:
        return load_csv_dataset(resolved_path)
    return load_parquet_dataset(resolved_path)
