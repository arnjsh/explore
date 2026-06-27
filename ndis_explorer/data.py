"""Data loading and validation.

Datasets are plain CSVs (see ``scripts/generate_sample_data.py`` for the bundled
synthetic sample). The loader supports two sources:

- ``"sample"`` - the tracked synthetic data under ``data/sample/``
- ``"user"``   - real NDIS exports the user drops into ``data/user/``

Both use identical file names / schemas so they are fully interchangeable. The
``NdisDataset`` container bundles the five related tables plus a couple of
convenience join helpers used throughout the analysis layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import DATASET_FILES, SAMPLE_DATA_DIR, USER_DATA_DIR

# Required columns per logical dataset, used for validation.
REQUIRED_COLUMNS: dict[str, set[str]] = {
    "regions": {"region_id", "region_name", "state", "remoteness", "population"},
    "market": {
        "region_id", "year", "active_participants",
        "committed_supports", "payments",
    },
    "support_categories": {
        "region_id", "year", "support_category", "budget_group",
        "committed_supports", "payments",
    },
    "providers": {
        "region_id", "year", "active_providers", "registered_providers",
    },
    "demographics": {"region_id", "segment_type", "segment", "participants"},
}


class DataValidationError(Exception):
    """Raised when a dataset is missing required columns or files."""


@dataclass
class NdisDataset:
    """Bundle of the five related NDIS tables.

    Attributes are raw, lightly-typed dataframes. Higher-level metrics live in
    :mod:`ndis_explorer.analysis` so this layer stays a thin, predictable I/O
    boundary.
    """

    regions: pd.DataFrame
    market: pd.DataFrame
    support_categories: pd.DataFrame
    providers: pd.DataFrame
    demographics: pd.DataFrame
    source: str = "sample"

    # -- convenience accessors ------------------------------------------- #
    @property
    def years(self) -> list[int]:
        return sorted(self.market["year"].unique().tolist())

    @property
    def latest_year(self) -> int:
        return max(self.years)

    @property
    def states(self) -> list[str]:
        return sorted(self.regions["state"].unique().tolist())

    def region_lookup(self) -> pd.DataFrame:
        """region_id -> name/state/remoteness/population (indexed by region_id)."""
        return self.regions.set_index("region_id")

    def market_with_regions(self) -> pd.DataFrame:
        """Market table enriched with region metadata and a utilisation column."""
        df = self.market.merge(self.regions, on="region_id", how="left")
        df["utilisation"] = (df["payments"] / df["committed_supports"]).clip(0, 1)
        return df


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise DataValidationError(f"Missing data file: {path}")
    return pd.read_csv(path)


def _validate(name: str, df: pd.DataFrame) -> None:
    required = REQUIRED_COLUMNS[name]
    missing = required - set(df.columns)
    if missing:
        raise DataValidationError(
            f"Dataset '{name}' is missing columns: {sorted(missing)}"
        )


def _coerce_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def data_dir_for(source: str) -> Path:
    if source == "sample":
        return SAMPLE_DATA_DIR
    if source == "user":
        return USER_DATA_DIR
    raise ValueError(f"Unknown data source '{source}' (expected 'sample'/'user')")


def user_data_available() -> bool:
    """True if the user has supplied a complete set of real exports."""
    return all((USER_DATA_DIR / fn).exists() for fn in DATASET_FILES.values())


def load_dataset(source: str = "sample") -> NdisDataset:
    """Load and validate a full :class:`NdisDataset` from the given source."""
    base = data_dir_for(source)
    frames: dict[str, pd.DataFrame] = {}
    for name, filename in DATASET_FILES.items():
        df = _read_csv(base / filename)
        _validate(name, df)
        frames[name] = df

    # Type coercion for the numeric columns we rely on.
    _coerce_numeric(
        frames["market"],
        ["year", "active_participants", "committed_supports", "payments"],
    )
    _coerce_numeric(
        frames["support_categories"],
        ["year", "committed_supports", "payments"],
    )
    _coerce_numeric(
        frames["providers"],
        ["year", "active_providers", "registered_providers"],
    )
    _coerce_numeric(frames["regions"], ["population"])
    _coerce_numeric(frames["demographics"], ["participants"])

    return NdisDataset(
        regions=frames["regions"],
        market=frames["market"],
        support_categories=frames["support_categories"],
        providers=frames["providers"],
        demographics=frames["demographics"],
        source=source,
    )


def resolve_source(prefer: str = "auto") -> str:
    """Pick a data source.

    ``"auto"`` uses real user data when a complete set is present, otherwise the
    bundled sample. Explicit ``"sample"``/``"user"`` are passed through.
    """
    if prefer == "auto":
        return "user" if user_data_available() else "sample"
    return prefer
