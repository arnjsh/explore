"""Narrative insight generation.

Two backends, same interface:

- **Rule-based** (always available): turns the computed metrics into clear,
  grounded prose. No network, no keys, fully deterministic.
- **LLM** (optional): if the ``openai`` package is installed and an
  ``OPENAI_API_KEY`` is set, the structured facts are handed to a model to write
  a richer brief. Any failure transparently falls back to the rule-based text.

Crucially, the LLM is only ever given **facts we computed** as grounding - it is
asked to summarise, not to invent figures - so insights stay trustworthy.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd

from .opportunity import explain_region


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #
def _fmt_money(value: float) -> str:
    if value is None or value != value:  # NaN
        return "n/a"
    for unit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(value) >= unit:
            return f"${value / unit:.1f}{suffix}"
    return f"${value:,.0f}"


def _fmt_pct(value: float, digits: int = 1) -> str:
    if value is None or value != value:
        return "n/a"
    return f"{value * 100:.{digits}f}%"


# --------------------------------------------------------------------------- #
# LLM availability
# --------------------------------------------------------------------------- #
def llm_available() -> bool:
    """True only if both the SDK and an API key are present."""
    if not os.environ.get("OPENAI_API_KEY"):
        return False
    try:
        import openai  # noqa: F401
    except ImportError:
        return False
    return True


@dataclass
class InsightResult:
    text: str
    backend: str  # "llm" or "rules"


# --------------------------------------------------------------------------- #
# Rule-based generators
# --------------------------------------------------------------------------- #
def _rule_based_market_brief(totals: dict, top_states: pd.DataFrame) -> str:
    lines = [
        f"In {totals['year']}, the (sample) NDIS market covers "
        f"**{totals['participants']:,} active participants** across "
        f"{totals['regions']} service regions, with "
        f"**{_fmt_money(totals['committed_supports'])} of committed supports** "
        f"and {_fmt_money(totals['payments'])} actually paid out "
        f"(**{_fmt_pct(totals['utilisation'])} utilisation**).",
        f"That leaves roughly **{_fmt_money(totals['unspent_supports'])} of "
        f"funded-but-unspent supports** - a headline signal of unmet demand that "
        f"new providers could capture.",
    ]
    if not top_states.empty:
        leader = top_states.iloc[0]
        lines.append(
            f"**{leader['state']}** is the largest market "
            f"({_fmt_money(leader['committed_supports'])} committed, "
            f"{int(leader['participants']):,} participants). "
            f"Across states, utilisation ranges from "
            f"{_fmt_pct(top_states['utilisation'].min())} to "
            f"{_fmt_pct(top_states['utilisation'].max())} - lower figures point "
            f"to thinner provider supply."
        )
    return "\n\n".join(lines)


def _rule_based_region_brief(exp: dict) -> str:
    util = exp.get("utilisation")
    ppp = exp.get("participants_per_provider")
    cagr = exp.get("participant_cagr")
    parts = [
        f"**{exp['region_name']} ({exp['state']}, {exp['remoteness']})** scores "
        f"**{exp['opportunity_score']:.0f}/100** for new-provider opportunity.",
        f"It has **{int(exp['participants']):,} active participants** and "
        f"**{_fmt_money(exp['committed_supports'])} of committed supports**, "
        f"growing at **{_fmt_pct(cagr)} per year**.",
    ]
    if ppp == ppp:  # not NaN
        parts.append(
            f"There are about **{ppp:.0f} participants per active provider** "
            + (
                "- a notably thin market that favours new entrants."
                if ppp >= 20
                else "- a relatively well-served market, so expect competition."
            )
        )
    if util == util:
        parts.append(
            f"Utilisation sits at **{_fmt_pct(util)}**"
            + (
                ", meaning a meaningful share of funded supports goes unspent "
                "(an unmet-need opening)."
                if util < 0.85
                else ", so most funded supports are already being delivered."
            )
        )
    if exp.get("top_driver"):
        parts.append(f"Its strongest driver is **{exp['top_driver']}**.")
    return " ".join(parts)


def _rule_based_opportunity_summary(scored: pd.DataFrame, n: int = 5) -> str:
    if scored.empty:
        return "No regions match the current filters."
    top = scored.head(n)
    bullet_lines = []
    for _, row in top.iterrows():
        exp = explain_region(row)
        bullet_lines.append(
            f"- **{exp['region_name']} ({exp['state']})** - score "
            f"{exp['opportunity_score']:.0f}; "
            f"{int(exp['participants']):,} participants, "
            f"{_fmt_money(exp['committed_supports'])} committed, "
            f"{_fmt_pct(exp['utilisation'])} utilisation, "
            f"~{exp['participants_per_provider']:.0f} participants/provider; "
            f"driver: {exp['top_driver']}."
        )
    header = (
        f"**Top {len(top)} opportunity regions** (of {len(scored)} matching the "
        f"current filters), ranked by the weighted opportunity score:"
    )
    return header + "\n\n" + "\n".join(bullet_lines)


# --------------------------------------------------------------------------- #
# LLM backend
# --------------------------------------------------------------------------- #
_SYSTEM_PROMPT = (
    "You are a market analyst advising someone who wants to start a new "
    "Australian NDIS (disability) service provider. You write concise, concrete "
    "briefs grounded ONLY in the figures provided. Never invent numbers. Use "
    "Australian context. Keep it under 200 words, use short paragraphs and bold "
    "key figures with markdown."
)


def _llm_complete(facts: str, instruction: str) -> str:
    from openai import OpenAI

    client = OpenAI()
    model = os.environ.get("NDIS_LLM_MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model,
        temperature=0.3,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"{instruction}\n\nGrounding facts:\n{facts}",
            },
        ],
    )
    return resp.choices[0].message.content.strip()


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def market_insight(
    totals: dict, top_states: pd.DataFrame, use_llm: bool = True
) -> InsightResult:
    """Narrative summary of the overall market."""
    rules = _rule_based_market_brief(totals, top_states)
    if use_llm and llm_available():
        try:
            text = _llm_complete(
                rules,
                "Write a punchy market-overview brief highlighting size, growth "
                "and where unmet demand sits.",
            )
            return InsightResult(text=text, backend="llm")
        except Exception:  # pragma: no cover - network/SDK failure path
            pass
    return InsightResult(text=rules, backend="rules")


def opportunity_insight(
    scored: pd.DataFrame, n: int = 5, use_llm: bool = True
) -> InsightResult:
    """Narrative ranking of the top opportunity regions."""
    rules = _rule_based_opportunity_summary(scored, n=n)
    if use_llm and llm_available() and not scored.empty:
        try:
            text = _llm_complete(
                rules,
                "Turn this ranked list into a brief recommending which regions to "
                "prioritise and why, noting any trade-offs (e.g. remoteness).",
            )
            return InsightResult(text=text, backend="llm")
        except Exception:  # pragma: no cover
            pass
    return InsightResult(text=rules, backend="rules")


def region_insight(row: pd.Series, use_llm: bool = True) -> InsightResult:
    """Narrative brief for a single scored region row."""
    exp = explain_region(row)
    rules = _rule_based_region_brief(exp)
    if use_llm and llm_available():
        try:
            text = _llm_complete(
                rules,
                "Write a short go/no-go style brief for launching a provider "
                "in this region.",
            )
            return InsightResult(text=text, backend="llm")
        except Exception:  # pragma: no cover
            pass
    return InsightResult(text=rules, backend="rules")
