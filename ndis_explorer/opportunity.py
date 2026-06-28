"""The opportunity-scoring model.

A deliberately **transparent**, explainable model: each region gets four
normalised 0-100 sub-scores, combined into a weighted average. No black boxes -
every input is a real, inspectable metric, and the weights are user-tunable.

Sub-scores (all higher = more attractive to a new provider):

- ``score_market_size``     committed supports $ (the size of the prize)
- ``score_growth``          participant CAGR (demand momentum)
- ``score_underservice``    participants per provider (thin supply = opening)
- ``score_utilisation_gap`` 1 - utilisation (funded need going unmet)

The combination of "lots of funded demand" + "few providers" + "money not being
spent" is the core thesis for where a new provider can win.
"""

from __future__ import annotations

import pandas as pd

from .analysis import percentile_rank, region_metrics
from .config import DEFAULT_WEIGHTS, OpportunityWeights
from .data import NdisDataset

SUBSCORE_COLUMNS = [
    "score_market_size",
    "score_growth",
    "score_underservice",
    "score_utilisation_gap",
]


def _normalise_weights(weights: OpportunityWeights) -> dict[str, float]:
    raw = weights.as_dict()
    total = sum(max(v, 0.0) for v in raw.values())
    if total <= 0:
        # Fall back to equal weighting if the user zeroes everything out.
        n = len(raw)
        return {k: 1.0 / n for k in raw}
    return {k: max(v, 0.0) / total for k, v in raw.items()}


def score_regions(
    dataset: NdisDataset,
    weights: OpportunityWeights | None = None,
    year: int | None = None,
    states: list[str] | None = None,
    remoteness: list[str] | None = None,
) -> pd.DataFrame:
    """Return the per-region metric table with opportunity sub-scores + score.

    Filtering by ``states`` / ``remoteness`` happens *before* normalisation so
    that scores are relative to the peer group the user is actually considering.
    """
    weights = weights or DEFAULT_WEIGHTS
    df = region_metrics(dataset, year=year)

    if states:
        df = df[df["state"].isin(states)]
    if remoteness:
        df = df[df["remoteness"].isin(remoteness)]

    df = df.copy()
    if df.empty:
        df["opportunity_score"] = []
        return df

    # Sub-scores via percentile rank (robust to skew). Utilisation gap is the
    # inverse of utilisation: low utilisation -> high gap -> high score.
    df["score_market_size"] = percentile_rank(df["committed_supports"])
    df["score_growth"] = percentile_rank(df["participant_cagr"])
    df["score_underservice"] = percentile_rank(df["participants_per_provider"])
    df["score_utilisation_gap"] = percentile_rank(1.0 - df["utilisation"])

    w = _normalise_weights(weights)
    df["opportunity_score"] = (
        df["score_market_size"] * w["market_size"]
        + df["score_growth"] * w["growth"]
        + df["score_underservice"] * w["underservice"]
        + df["score_utilisation_gap"] * w["utilisation_gap"]
    )

    df["opportunity_rank"] = (
        df["opportunity_score"].rank(ascending=False, method="min").astype(int)
    )
    return df.sort_values("opportunity_score", ascending=False).reset_index(drop=True)


def top_opportunities(
    dataset: NdisDataset,
    n: int = 10,
    weights: OpportunityWeights | None = None,
    **kwargs,
) -> pd.DataFrame:
    """Convenience: the top-N scored regions."""
    return score_regions(dataset, weights=weights, **kwargs).head(n)


def explain_region(row: pd.Series) -> dict[str, object]:
    """Produce a structured explanation for a single scored region row.

    Returns the headline score plus the ranked contribution of each sub-score,
    which the AI/insight layer and UI use to justify *why* a region scored well.
    """
    drivers = {
        "Market size": row.get("score_market_size", float("nan")),
        "Growth momentum": row.get("score_growth", float("nan")),
        "Under-servicing": row.get("score_underservice", float("nan")),
        "Utilisation gap": row.get("score_utilisation_gap", float("nan")),
    }
    ranked = sorted(
        drivers.items(),
        key=lambda kv: (kv[1] if kv[1] == kv[1] else -1),  # NaN-safe
        reverse=True,
    )
    return {
        "region_name": row.get("region_name"),
        "state": row.get("state"),
        "remoteness": row.get("remoteness"),
        "opportunity_score": row.get("opportunity_score"),
        "participants": row.get("active_participants"),
        "committed_supports": row.get("committed_supports"),
        "utilisation": row.get("utilisation"),
        "participants_per_provider": row.get("participants_per_provider"),
        "participant_cagr": row.get("participant_cagr"),
        "drivers": ranked,
        "top_driver": ranked[0][0] if ranked else None,
    }
