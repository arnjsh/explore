"""Tests for the insight generator (rule-based path)."""

from __future__ import annotations

from ndis_explorer.ai import (
    _fmt_money,
    _fmt_pct,
    llm_available,
    market_insight,
    opportunity_insight,
    region_insight,
)
from ndis_explorer.analysis import national_totals, state_summary
from ndis_explorer.opportunity import score_regions


def test_fmt_money():
    assert _fmt_money(1_500_000_000) == "$1.5B"
    assert _fmt_money(2_500_000) == "$2.5M"
    assert _fmt_money(3_400) == "$3.4K"
    assert _fmt_money(float("nan")) == "n/a"


def test_fmt_pct():
    assert _fmt_pct(0.123) == "12.3%"
    assert _fmt_pct(float("nan")) == "n/a"


def test_llm_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert llm_available() is False


def test_market_insight_rules(monkeypatch, dataset):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    totals = national_totals(dataset)
    states = state_summary(dataset)
    res = market_insight(totals, states, use_llm=True)
    assert res.backend == "rules"
    assert "participants" in res.text.lower()


def test_opportunity_insight_rules(monkeypatch, dataset):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    scored = score_regions(dataset)
    res = opportunity_insight(scored, n=3, use_llm=True)
    assert res.backend == "rules"
    assert "opportunity" in res.text.lower()


def test_opportunity_insight_handles_empty(dataset):
    scored = score_regions(dataset, states=["ZZ"])
    res = opportunity_insight(scored, use_llm=False)
    assert "No regions" in res.text


def test_region_insight_rules(monkeypatch, dataset):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    scored = score_regions(dataset)
    res = region_insight(scored.iloc[0], use_llm=True)
    assert res.backend == "rules"
    assert "/100" in res.text or "score" in res.text.lower()
