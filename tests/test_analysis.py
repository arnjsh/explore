"""Tests for the analysis layer."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ndis_explorer.analysis import (
    cagr,
    category_metrics,
    demographic_summary,
    market_timeseries,
    minmax,
    national_totals,
    percentile_rank,
    region_metrics,
    state_summary,
)


def test_cagr_basic():
    # Doubling over 2 periods => ~41.4% CAGR.
    assert cagr(100, 200, 2) == (2 ** 0.5 - 1)
    assert np.isnan(cagr(0, 100, 2))
    assert np.isnan(cagr(100, 100, 0))


def test_percentile_rank_range():
    s = pd.Series([1, 2, 3, 4])
    pr = percentile_rank(s)
    assert pr.min() > 0
    assert pr.max() == 100.0


def test_percentile_rank_degenerate():
    s = pd.Series([5, 5, 5])
    pr = percentile_rank(s)
    assert (pr == 50.0).all()


def test_minmax_range():
    s = pd.Series([10, 20, 30])
    mm = minmax(s)
    assert mm.iloc[0] == 0.0
    assert mm.iloc[-1] == 100.0


def test_region_metrics_columns(dataset):
    rm = region_metrics(dataset)
    for col in (
        "utilisation", "participants_per_provider", "participant_cagr",
        "demand_supply_gap_cagr", "avg_committed_per_participant",
    ):
        assert col in rm.columns
    assert (rm["utilisation"] >= 0).all() and (rm["utilisation"] <= 1).all()
    assert (rm["participants_per_provider"] > 0).all()


def test_region_metrics_year_filter(dataset):
    year = dataset.years[0]
    rm = region_metrics(dataset, year=year)
    assert (rm["year"] == year).all()


def test_national_totals(dataset):
    totals = national_totals(dataset)
    assert totals["participants"] > 0
    assert totals["committed_supports"] >= totals["payments"]
    assert 0 <= totals["utilisation"] <= 1


def test_state_summary_sums(dataset):
    states = state_summary(dataset)
    rm = region_metrics(dataset)
    assert states["participants"].sum() == rm["active_participants"].sum()


def test_market_timeseries_sorted(dataset):
    ts = market_timeseries(dataset)
    assert list(ts["year"]) == sorted(ts["year"])
    assert (ts["committed_supports"] >= ts["payments"]).all()


def test_category_metrics(dataset):
    cats = category_metrics(dataset)
    assert not cats.empty
    assert {"committed_supports", "utilisation", "yoy_growth"}.issubset(cats.columns)
    assert (cats["utilisation"] >= 0).all()


def test_category_metrics_state_filter(dataset):
    one = dataset.states[0]
    filtered = category_metrics(dataset, states=[one])
    national = category_metrics(dataset)
    assert filtered["committed_supports"].sum() <= national["committed_supports"].sum()


def test_demographic_summary_shares(dataset):
    summ = demographic_summary(dataset, "disability_type")
    assert abs(summ["share"].sum() - 1.0) < 1e-6
