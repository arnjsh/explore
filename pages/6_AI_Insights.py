"""AI Insights - auto-written briefs grounded in the computed metrics."""

from __future__ import annotations

import streamlit as st

from ndis_explorer.ai import (
    llm_available,
    market_insight,
    opportunity_insight,
)
from ndis_explorer.analysis import national_totals, state_summary
from ndis_explorer.opportunity import score_regions
from ndis_explorer.streamlit_helpers import (
    configure_page,
    data_source_caption,
    get_dataset,
    region_filter_controls,
    sidebar_data_controls,
    weight_controls,
)

configure_page("AI Insights", icon="🤖")
dataset = get_dataset()
sidebar_data_controls(dataset)
weights = weight_controls()
states, remoteness, year = region_filter_controls(dataset)

st.title("🤖 AI Insights")
data_source_caption(dataset)

if llm_available():
    st.success(
        "LLM backend **enabled** - briefs are written by an LLM, grounded in the "
        "figures this app computes.",
        icon="✅",
    )
else:
    st.info(
        "No `OPENAI_API_KEY` detected - using the built-in **rule-based** writer. "
        "Set the env var (and `pip install openai`) to enable LLM briefs. "
        "Everything below still works.",
        icon="ℹ️",
    )

use_llm = st.toggle("Use LLM if available", value=True)

st.subheader("Market overview brief")
totals = national_totals(dataset, year=year)
states_summary = state_summary(dataset, year=year)
if st.button("Generate market brief", type="primary"):
    with st.spinner("Writing..."):
        res = market_insight(totals, states_summary, use_llm=use_llm)
    st.markdown(res.text)
    st.caption(f"Backend: {res.backend}")

st.divider()

st.subheader("Opportunity brief")
st.caption("Uses the sidebar weights and filters.")
scored = score_regions(
    dataset, weights=weights, year=year,
    states=states or None, remoteness=remoteness or None,
)
n = st.slider("How many regions to cover", 3, 10, 5)
if st.button("Generate opportunity brief", type="primary"):
    with st.spinner("Writing..."):
        res = opportunity_insight(scored, n=n, use_llm=use_llm)
    st.markdown(res.text)
    st.caption(f"Backend: {res.backend}")

with st.expander("How grounding works"):
    st.markdown(
        """
The LLM is **never** asked to make up numbers. The app computes every figure
(market size, growth, utilisation, participants-per-provider, scores) and passes
them to the model as *grounding facts*, asking only for a readable summary. If
the model is unavailable or errors, the same facts are rendered by a
deterministic rule-based writer instead — so output is always trustworthy and
reproducible.
        """
    )
