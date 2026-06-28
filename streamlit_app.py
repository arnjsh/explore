"""NDIS Opportunity Explorer - Streamlit entry point (Home).

Run with::

    streamlit run streamlit_app.py

Streamlit auto-discovers the multi-page UI in the ``pages/`` directory.
"""

from __future__ import annotations

import streamlit as st

from ndis_explorer.ai import llm_available
from ndis_explorer.analysis import national_totals, state_summary
from ndis_explorer.config import APP
from ndis_explorer.streamlit_helpers import (
    configure_page,
    data_source_caption,
    fmt_money,
    fmt_pct,
    get_dataset,
    sidebar_data_controls,
)

configure_page("Home", icon="🧭")

dataset = get_dataset()
sidebar_data_controls(dataset)

st.title(f"🧭 {APP.name}")
st.subheader(APP.tagline)
data_source_caption(dataset)
st.info(APP.disclaimer, icon="ℹ️")

# Headline metrics for the latest year.
totals = national_totals(dataset)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Active participants", f"{totals['participants']:,}")
c2.metric("Committed supports", fmt_money(totals["committed_supports"]))
c3.metric("Utilisation", fmt_pct(totals["utilisation"]))
c4.metric("Funded but unspent", fmt_money(totals["unspent_supports"]))

st.divider()

left, right = st.columns([3, 2])
with left:
    st.markdown(
        """
### What this app does

This is a **local-first** research tool for sizing the Australian NDIS market
and finding **where a new disability service provider could win**. It combines
market sizing, growth trends, provider supply and funding-utilisation gaps into
a single, transparent **opportunity score**.

#### Where to go next
- **📊 Market Overview** - national & state size, growth and utilisation trends
- **🎯 Opportunity Finder** - ranked regions with a tunable scoring model
- **🗺️ Regional Explorer** - drill into any single region
- **🧩 Support Categories** - which services have the most unmet, growing demand
- **👥 Demographics** - participant mix by disability, age and plan management
- **🤖 AI Insights** - auto-written briefs grounded in the computed metrics
- **📁 Data Manager** - swap the sample for real `data.ndis.gov.au` exports
        """
    )
with right:
    st.markdown("#### The opportunity thesis")
    st.markdown(
        """
A strong opening for a new provider tends to combine:

1. **Sizeable funded demand** (committed supports $)
2. **Fast participant growth** (momentum)
3. **Thin provider supply** (high participants-per-provider)
4. **A utilisation gap** (funded supports going unspent)

The **Opportunity Finder** lets you weight these to match your strategy.
        """
    )
    st.markdown("#### Status")
    st.write(
        "🤖 LLM insights: "
        + ("**enabled** (`OPENAI_API_KEY` found)" if llm_available()
           else "**rule-based** (no API key — still fully functional)")
    )

st.divider()
st.markdown("##### Largest markets by committed supports (latest year)")
states = state_summary(dataset)
show = states.assign(
    committed=lambda d: d["committed_supports"].map(fmt_money),
    paid=lambda d: d["payments"].map(fmt_money),
    util=lambda d: d["utilisation"].map(fmt_pct),
    ppp=lambda d: d["participants_per_provider"].round(0),
)[["state", "regions", "participants", "committed", "paid", "util", "ppp"]]
show.columns = [
    "State", "Regions", "Participants", "Committed", "Paid",
    "Utilisation", "Participants/Provider",
]
st.dataframe(show, hide_index=True, use_container_width=True)

st.caption(f"v{APP.version} · For personal research only.")
