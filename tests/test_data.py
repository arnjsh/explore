"""Tests for the data loading / validation layer."""

from __future__ import annotations

import pandas as pd
import pytest

from ndis_explorer.config import DATASET_FILES, STATES
from ndis_explorer.data import (
    REQUIRED_COLUMNS,
    DataValidationError,
    NdisDataset,
    _validate,
    load_dataset,
    resolve_source,
)


def test_sample_dataset_loads(dataset: NdisDataset):
    assert isinstance(dataset, NdisDataset)
    assert dataset.source == "sample"
    assert not dataset.regions.empty
    assert not dataset.market.empty


def test_all_files_present():
    # Every logical dataset maps to a real file name.
    assert set(DATASET_FILES) == set(REQUIRED_COLUMNS)


def test_required_columns_present(dataset: NdisDataset):
    for name, required in REQUIRED_COLUMNS.items():
        df = getattr(
            dataset,
            "support_categories" if name == "support_categories" else name,
        )
        assert required.issubset(set(df.columns)), name


def test_years_and_states(dataset: NdisDataset):
    assert len(dataset.years) >= 2
    assert dataset.latest_year == max(dataset.years)
    assert set(dataset.states).issubset(set(STATES))


def test_referential_integrity(dataset: NdisDataset):
    region_ids = set(dataset.regions["region_id"])
    for df in (dataset.market, dataset.providers, dataset.demographics):
        assert set(df["region_id"]).issubset(region_ids)


def test_market_with_regions_has_utilisation(dataset: NdisDataset):
    df = dataset.market_with_regions()
    assert "utilisation" in df.columns
    assert (df["utilisation"] >= 0).all()
    assert (df["utilisation"] <= 1).all()


def test_validate_raises_on_missing_columns():
    bad = pd.DataFrame({"region_id": [1]})
    with pytest.raises(DataValidationError):
        _validate("regions", bad)


def test_resolve_source_defaults_to_sample(monkeypatch):
    # With no user data, auto should resolve to sample.
    monkeypatch.setattr("ndis_explorer.data.user_data_available", lambda: False)
    assert resolve_source("auto") == "sample"
    assert resolve_source("sample") == "sample"


def test_load_unknown_source_raises():
    with pytest.raises(ValueError):
        load_dataset("nonsense")
