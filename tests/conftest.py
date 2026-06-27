"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from ndis_explorer.data import NdisDataset, load_dataset


@pytest.fixture(scope="session")
def dataset() -> NdisDataset:
    """The bundled synthetic sample dataset."""
    return load_dataset("sample")
