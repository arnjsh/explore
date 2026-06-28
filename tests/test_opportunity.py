"""Tests for the opportunity-scoring model."""

from __future__ import annotations

from ndis_explorer.config import OpportunityWeights
from ndis_explorer.opportunity import (
    SUBSCORE_COLUMNS,
    _normalise_weights,
    explain_region,
    score_regions,
    top_opportunities,
)


def test_score_regions_basic(dataset):
    scored = score_regions(dataset)
    assert not scored.empty
    assert "opportunity_score" in scored.columns
    # Scores are a weighted average of 0-100 sub-scores => stay in range.
    assert scored["opportunity_score"].between(0, 100).all()
    for col in SUBSCORE_COLUMNS:
        assert scored[col].between(0, 100).all()


def test_scores_sorted_descending(dataset):
    scored = score_regions(dataset)
    vals = scored["opportunity_score"].tolist()
    assert vals == sorted(vals, reverse=True)
    assert scored["opportunity_rank"].iloc[0] == 1


def test_weights_change_ranking(dataset):
    only_size = OpportunityWeights(
        market_size=1, growth=0, underservice=0, utilisation_gap=0
    )
    only_under = OpportunityWeights(
        market_size=0, growth=0, underservice=1, utilisation_gap=0
    )
    a = score_regions(dataset, weights=only_size)
    b = score_regions(dataset, weights=only_under)
    # Different single-factor weightings should generally yield a different top.
    assert a.iloc[0]["region_id"] != b.iloc[0]["region_id"] or len(a) == 1


def test_normalise_weights_sums_to_one():
    w = _normalise_weights(OpportunityWeights(1, 1, 1, 1))
    assert abs(sum(w.values()) - 1.0) < 1e-9


def test_normalise_weights_all_zero_is_equal():
    w = _normalise_weights(OpportunityWeights(0, 0, 0, 0))
    assert all(abs(v - 0.25) < 1e-9 for v in w.values())


def test_state_filter(dataset):
    state = dataset.states[0]
    scored = score_regions(dataset, states=[state])
    assert (scored["state"] == state).all()


def test_empty_filter_returns_empty(dataset):
    scored = score_regions(dataset, states=["ZZ"])
    assert scored.empty


def test_top_opportunities_limit(dataset):
    top = top_opportunities(dataset, n=3)
    assert len(top) == 3


def test_explain_region(dataset):
    scored = score_regions(dataset)
    exp = explain_region(scored.iloc[0])
    assert exp["region_name"]
    assert len(exp["drivers"]) == 4
    # Drivers are sorted descending by sub-score.
    scores = [v for _, v in exp["drivers"]]
    assert scores == sorted(scores, reverse=True)
    assert exp["top_driver"] == exp["drivers"][0][0]
