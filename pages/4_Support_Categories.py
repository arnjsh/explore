"""Support Categories - which services have unmet, growing demand."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from ndis_explorer.analysis import category_metrics, category_timeseries
from ndis_explorer.config import STATES
from ndis_explorer.streamlit_helpers import (
    configure_page,
    data_source_caption,
    fmt_money,
    fmt_pct,
    get_dataset,
    sidebar_data_controls,
)

configure_page("Support Categories", icon="🧩")
dataset = get_dataset()
sidebar_data_controls(dataset)

st.title("🧩 Support Categories")
data_source_caption(dataset)
st.markdown(
    "Where the money is, where it is **growing**, and where it is **not being "
    "spent**. Categories with high committed supports, strong growth and low "
    "utilisation are the clearest service-line opportunities."
)

with st.sidebar:
    st.markdown("#### Filters")
    sel_states = st.multiselect(
        "States / territories",
        options=[s for s in STATES if s in dataset.states],
        default=[],
        help="Empty = national.",
    )
    year = st.select_slider("Year", options=dataset.years, value=dataset.latest_year)

cats = category_metrics(dataset, year=year, states=sel_states or None)

# --- Funding by category, coloured by utilisation ---------------------- #
col1, col2 = st.columns([3, 2])
with col1:
    st.subheader("Committed supports by category")
    fig = px.bar(
        cats.sort_values("committed_supports"),
        x="committed_supports", y="support_category", orientation="h",
        color="utilisation", color_continuous_scale="RdYlGn",
        labels={"committed_supports": "Committed (AUD)", "support_category": ""},
        hover_data={"budget_group": True},
    )
    fig.update_layout(coloraxis_colorbar_title="Util.")
    st.plotly_chart(fig, use_container_width=True)
with col2:
    st.subheader("Growth vs utilisation")
    fig = px.scatter(
        cats, x="utilisation", y="yoy_growth",
        size="committed_supports", color="budget_group", text="support_category",
        labels={"utilisation": "Utilisation", "yoy_growth": "YoY growth"},
    )
    fig.update_traces(textposition="top center")
    fig.update_xaxes(tickformat=".0%")
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Top-left = growing fast **and** under-utilised = best opening.")

# --- Budget group rollup ----------------------------------------------- #
st.subheader("By budget group")
group = (
    cats.groupby("budget_group")
    .agg(committed=("committed_supports", "sum"),
         paid=("payments", "sum"),
         unspent=("unspent_supports", "sum"))
    .reset_index()
)
group["utilisation"] = (group["paid"] / group["committed"]).clip(0, 1)
gcols = st.columns(len(group))
for col, (_, r) in zip(gcols, group.iterrows()):
    col.metric(
        r["budget_group"],
        fmt_money(r["committed"]),
        delta=f"{fmt_pct(r['utilisation'])} utilised",
        delta_color="off",
    )

# --- Detail table ------------------------------------------------------ #
show = cats.assign(
    Committed=lambda d: d["committed_supports"].map(fmt_money),
    Paid=lambda d: d["payments"].map(fmt_money),
    Unspent=lambda d: d["unspent_supports"].map(fmt_money),
    Utilisation=lambda d: d["utilisation"].map(fmt_pct),
    Growth=lambda d: d["yoy_growth"].map(fmt_pct),
)[
    ["support_category", "budget_group", "Committed", "Paid", "Unspent",
     "Utilisation", "Growth"]
].rename(columns={"support_category": "Category", "budget_group": "Group"})
st.dataframe(show, hide_index=True, use_container_width=True)

# --- Single-category trend --------------------------------------------- #
st.subheader("Category trend")
cat = st.selectbox("Category", cats["support_category"].tolist())
ts = category_timeseries(dataset, cat)
fig = px.line(ts, x="year", y=["committed_supports", "payments"], markers=True,
              labels={"value": "AUD", "year": "Year", "variable": ""})
st.plotly_chart(fig, use_container_width=True)
