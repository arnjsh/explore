"""Market analysis: sizing, growth and derived per-region metrics.

This layer turns the raw tables in :class:`~ndis_explorer.data.NdisDataset` into
the analytical frames the UI and the opportunity model consume. Everything here
is pure pandas/numpy and side-effect free, which keeps it trivially testable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .data import NdisDataset


# --------------------------------------------------------------------------- #
# Normalisation helpers
# --------------------------------------------------------------------------- #
def percentile_rank(series: pd.Series) -> pd.Series:
    """Rank-normalise a series to 0-100 (robust to outliers/skew).

    Using percentile rank rather than raw min-max means a few huge metro markets
    do not flatten the rest of the distribution to ~0.
    """
    s = series.astype(float)
    if s.notna().sum() <= 1 or s.nunique() <= 1:
        # Degenerate: everything identical -> neutral 50.
        return pd.Series(50.0, index=s.index)
    return s.rank(pct=True) * 100.0


def minmax(series: pd.Series) -> pd.Series:
    """Min-max scale a series to 0-100."""
    s = series.astype(float)
    lo, hi = s.min(), s.max()
    if not np.isfinite(lo) or not np.isfinite(hi) or hi == lo:
        return pd.Series(50.0, index=s.index)
    return (s - lo) / (hi - lo) * 100.0


def cagr(start: float, end: float, periods: int) -> float:
    """Compound annual growth rate. Returns NaN for invalid inputs."""
    if periods <= 0 or start is None or end is None or start <= 0 or end <= 0:
        return float("nan")
    return (end / start) ** (1.0 / periods) - 1.0


# --------------------------------------------------------------------------- #
# Growth
# --------------------------------------------------------------------------- #
def region_growth(dataset: NdisDataset) -> pd.DataFrame:
    """Per-region CAGR of participants and committed supports across all years."""
    rows = []
    for region_id, grp in dataset.market.groupby("region_id"):
        grp = grp.sort_values("year")
        periods = int(grp["year"].iloc[-1] - grp["year"].iloc[0])
        rows.append(
            {
                "region_id": region_id,
                "participant_cagr": cagr(
                    grp["active_participants"].iloc[0],
                    grp["active_participants"].iloc[-1],
                    periods,
                ),
                "committed_cagr": cagr(
                    grp["committed_supports"].iloc[0],
                    grp["committed_supports"].iloc[-1],
                    periods,
                ),
            }
        )
    return pd.DataFrame(rows)


def provider_growth(dataset: NdisDataset) -> pd.DataFrame:
    """Per-region CAGR of active providers across all years."""
    rows = []
    for region_id, grp in dataset.providers.groupby("region_id"):
        grp = grp.sort_values("year")
        periods = int(grp["year"].iloc[-1] - grp["year"].iloc[0])
        rows.append(
            {
                "region_id": region_id,
                "provider_cagr": cagr(
                    grp["active_providers"].iloc[0],
                    grp["active_providers"].iloc[-1],
                    periods,
                ),
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Per-region snapshot
# --------------------------------------------------------------------------- #
def region_metrics(dataset: NdisDataset, year: int | None = None) -> pd.DataFrame:
    """Build the core per-region metric table for a given (default latest) year.

    Columns include market size, utilisation, provider supply, the key
    ``participants_per_provider`` under-servicing ratio, and multi-year growth.
    """
    year = year or dataset.latest_year

    market = dataset.market[dataset.market["year"] == year].copy()
    providers = dataset.providers[dataset.providers["year"] == year].copy()

    df = (
        dataset.regions.merge(market, on="region_id", how="inner")
        .merge(providers, on="region_id", how="left")
        .merge(region_growth(dataset), on="region_id", how="left")
        .merge(provider_growth(dataset), on="region_id", how="left")
    )

    df["utilisation"] = (df["payments"] / df["committed_supports"]).clip(0, 1)
    df["unspent_supports"] = (df["committed_supports"] - df["payments"]).clip(lower=0)
    df["active_providers"] = df["active_providers"].fillna(0)
    df["participants_per_provider"] = np.where(
        df["active_providers"] > 0,
        df["active_participants"] / df["active_providers"],
        np.nan,
    )
    df["avg_committed_per_participant"] = (
        df["committed_supports"] / df["active_participants"]
    )
    # Demand growing faster than supply -> widening gap (positive = good for entrants).
    df["demand_supply_gap_cagr"] = df["participant_cagr"] - df["provider_cagr"]
    df["year"] = year
    return df


# --------------------------------------------------------------------------- #
# Aggregations
# --------------------------------------------------------------------------- #
def state_summary(dataset: NdisDataset, year: int | None = None) -> pd.DataFrame:
    """Aggregate the per-region snapshot up to state level."""
    rm = region_metrics(dataset, year)
    agg = (
        rm.groupby("state")
        .agg(
            regions=("region_id", "nunique"),
            participants=("active_participants", "sum"),
            committed_supports=("committed_supports", "sum"),
            payments=("payments", "sum"),
            active_providers=("active_providers", "sum"),
            population=("population", "sum"),
        )
        .reset_index()
    )
    agg["utilisation"] = (agg["payments"] / agg["committed_supports"]).clip(0, 1)
    agg["participants_per_provider"] = np.where(
        agg["active_providers"] > 0,
        agg["participants"] / agg["active_providers"],
        np.nan,
    )
    agg["participation_rate"] = agg["participants"] / agg["population"]
    return agg.sort_values("committed_supports", ascending=False)


def national_totals(dataset: NdisDataset, year: int | None = None) -> dict[str, float]:
    """Headline national figures for the chosen year."""
    rm = region_metrics(dataset, year)
    committed = float(rm["committed_supports"].sum())
    payments = float(rm["payments"].sum())
    return {
        "year": rm["year"].iloc[0],
        "participants": int(rm["active_participants"].sum()),
        "committed_supports": committed,
        "payments": payments,
        "unspent_supports": max(committed - payments, 0.0),
        "utilisation": (payments / committed) if committed else float("nan"),
        "active_providers": int(rm["active_providers"].sum()),
        "regions": int(rm["region_id"].nunique()),
    }


def market_timeseries(dataset: NdisDataset) -> pd.DataFrame:
    """National totals per year (for trend charts)."""
    ts = (
        dataset.market.groupby("year")
        .agg(
            participants=("active_participants", "sum"),
            committed_supports=("committed_supports", "sum"),
            payments=("payments", "sum"),
        )
        .reset_index()
    )
    providers = (
        dataset.providers.groupby("year")["active_providers"].sum().reset_index()
    )
    ts = ts.merge(providers, on="year", how="left")
    ts["utilisation"] = (ts["payments"] / ts["committed_supports"]).clip(0, 1)
    return ts.sort_values("year")


# --------------------------------------------------------------------------- #
# Support categories
# --------------------------------------------------------------------------- #
def category_metrics(
    dataset: NdisDataset,
    year: int | None = None,
    states: list[str] | None = None,
) -> pd.DataFrame:
    """Aggregate support-category economics, optionally filtered to states.

    Includes a YoY growth column (committed supports) and a utilisation column.
    Low utilisation flags categories where funded need is not being met - a
    classic provider-entry signal (e.g. Support Coordination, Assistive Tech).
    """
    year = year or dataset.latest_year
    sc = dataset.support_categories.merge(
        dataset.regions[["region_id", "state"]], on="region_id", how="left"
    )
    if states:
        sc = sc[sc["state"].isin(states)]

    current = sc[sc["year"] == year]
    agg = (
        current.groupby(["support_category", "budget_group"])
        .agg(
            committed_supports=("committed_supports", "sum"),
            payments=("payments", "sum"),
        )
        .reset_index()
    )
    agg["utilisation"] = (agg["payments"] / agg["committed_supports"]).clip(0, 1)
    agg["unspent_supports"] = (agg["committed_supports"] - agg["payments"]).clip(lower=0)

    # YoY growth vs the previous available year.
    prev_year = max([y for y in dataset.years if y < year], default=None)
    if prev_year is not None:
        prev = (
            sc[sc["year"] == prev_year]
            .groupby("support_category")["committed_supports"]
            .sum()
            .rename("committed_prev")
        )
        agg = agg.merge(prev, on="support_category", how="left")
        agg["yoy_growth"] = (
            agg["committed_supports"] / agg["committed_prev"] - 1.0
        )
    else:
        agg["yoy_growth"] = float("nan")

    return agg.sort_values("committed_supports", ascending=False)


def category_timeseries(
    dataset: NdisDataset, category: str
) -> pd.DataFrame:
    """National committed/payments per year for a single support category."""
    sc = dataset.support_categories
    sc = sc[sc["support_category"] == category]
    ts = (
        sc.groupby("year")
        .agg(
            committed_supports=("committed_supports", "sum"),
            payments=("payments", "sum"),
        )
        .reset_index()
        .sort_values("year")
    )
    ts["utilisation"] = (ts["payments"] / ts["committed_supports"]).clip(0, 1)
    return ts


# --------------------------------------------------------------------------- #
# Demographics
# --------------------------------------------------------------------------- #
def demographic_summary(
    dataset: NdisDataset,
    segment_type: str,
    region_ids: list[str] | None = None,
) -> pd.DataFrame:
    """Aggregate participant counts for one segment type (optionally by region)."""
    demo = dataset.demographics
    demo = demo[demo["segment_type"] == segment_type]
    if region_ids:
        demo = demo[demo["region_id"].isin(region_ids)]
    agg = (
        demo.groupby("segment")["participants"].sum().reset_index()
        .sort_values("participants", ascending=False)
    )
    total = agg["participants"].sum()
    agg["share"] = agg["participants"] / total if total else float("nan")
    return agg
