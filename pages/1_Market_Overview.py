"""Market Overview - national & state sizing, growth and utilisation."""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ndis_explorer.analysis import (
    market_timeseries,
    national_totals,
    state_summary,
)
from ndis_explorer.streamlit_helpers import (
    configure_page,
    data_source_caption,
    fmt_money,
    fmt_pct,
    get_dataset,
    sidebar_data_controls,
)

configure_page("Market Overview", icon="📊")
dataset = get_dataset()
sidebar_data_controls(dataset)

st.title("📊 Market Overview")
data_source_caption(dataset)

totals = national_totals(dataset)
ts = market_timeseries(dataset)
first, last = ts.iloc[0], ts.iloc[-1]
years_span = max(int(last["year"] - first["year"]), 1)
part_growth = (last["participants"] / first["participants"]) ** (1 / years_span) - 1
fund_growth = (
    last["committed_supports"] / first["committed_supports"]
) ** (1 / years_span) - 1

c1, c2, c3, c4 = st.columns(4)
c1.metric("Active participants", f"{totals['participants']:,}",
          delta=f"{fmt_pct(part_growth)}/yr")
c2.metric("Committed supports", fmt_money(totals["committed_supports"]),
          delta=f"{fmt_pct(fund_growth)}/yr")
c3.metric("Utilisation", fmt_pct(totals["utilisation"]))
c4.metric("Active providers", f"{totals['active_providers']:,}")

st.divider()

# --- Trend charts ------------------------------------------------------- #
st.subheader("National trends")
t1, t2, t3 = st.tabs(["Participants", "Funding (committed vs paid)", "Utilisation"])

with t1:
    fig = px.area(
        ts, x="year", y="participants",
        labels={"participants": "Active participants", "year": "Year"},
    )
    fig.update_traces(line_color="#2563eb", fillcolor="rgba(37,99,235,0.2)")
    st.plotly_chart(fig, use_container_width=True)

with t2:
    fig = go.Figure()
    fig.add_bar(x=ts["year"], y=ts["committed_supports"], name="Committed",
                marker_color="#93c5fd")
    fig.add_bar(x=ts["year"], y=ts["payments"], name="Paid",
                marker_color="#2563eb")
    fig.update_layout(barmode="overlay", xaxis_title="Year",
                      yaxis_title="AUD", legend_title="")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "The gap between committed and paid is **funded-but-unspent** support - "
        "a proxy for unmet demand."
    )

with t3:
    fig = px.line(ts, x="year", y="utilisation", markers=True,
                  labels={"utilisation": "Utilisation", "year": "Year"})
    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    fig.update_traces(line_color="#16a34a")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- State comparison --------------------------------------------------- #
st.subheader("By state / territory")
states = state_summary(dataset)

col1, col2 = st.columns(2)
with col1:
    fig = px.bar(
        states.sort_values("committed_supports"),
        x="committed_supports", y="state", orientation="h",
        labels={"committed_supports": "Committed supports (AUD)", "state": ""},
        color="utilisation", color_continuous_scale="RdYlGn",
    )
    fig.update_layout(coloraxis_colorbar_title="Util.")
    st.plotly_chart(fig, use_container_width=True)
with col2:
    fig = px.scatter(
        states, x="participants_per_provider", y="utilisation",
        size="committed_supports", color="state", text="state",
        labels={
            "participants_per_provider": "Participants per provider (supply)",
            "utilisation": "Utilisation (delivery)",
        },
    )
    fig.update_traces(textposition="top center")
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Bottom-right = thin supply **and** low utilisation = most under-served."
    )

show = states.assign(
    committed=lambda d: d["committed_supports"].map(fmt_money),
    paid=lambda d: d["payments"].map(fmt_money),
    util=lambda d: d["utilisation"].map(fmt_pct),
    rate=lambda d: d["participation_rate"].map(lambda v: fmt_pct(v, 2)),
    ppp=lambda d: d["participants_per_provider"].round(0),
)[["state", "regions", "participants", "committed", "paid", "util", "rate", "ppp"]]
show.columns = [
    "State", "Regions", "Participants", "Committed", "Paid", "Utilisation",
    "Participation rate", "Participants/Provider",
]
st.dataframe(show, hide_index=True, use_container_width=True)
