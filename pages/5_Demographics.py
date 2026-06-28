"""Demographics - participant mix by disability, age and plan management."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from ndis_explorer.analysis import demographic_summary
from ndis_explorer.config import STATES
from ndis_explorer.streamlit_helpers import (
    configure_page,
    data_source_caption,
    fmt_pct,
    get_dataset,
    sidebar_data_controls,
)

configure_page("Demographics", icon="👥")
dataset = get_dataset()
sidebar_data_controls(dataset)

st.title("👥 Demographics")
data_source_caption(dataset)
st.markdown(
    "Understand *who* the participants are. Disability mix, age profile and plan "
    "management split all shape which services to offer and how to reach people."
)

with st.sidebar:
    st.markdown("#### Filters")
    sel_states = st.multiselect(
        "States / territories",
        options=[s for s in STATES if s in dataset.states],
        default=[],
        help="Empty = national.",
    )

if sel_states:
    region_ids = dataset.regions[
        dataset.regions["state"].isin(sel_states)
    ]["region_id"].tolist()
else:
    region_ids = None

SEGMENTS = (
    ("disability_type", "Primary disability"),
    ("age_band", "Age band"),
    ("plan_management", "Plan management"),
)

for seg_type, title in SEGMENTS:
    st.subheader(title)
    summ = demographic_summary(dataset, seg_type, region_ids=region_ids)
    col1, col2 = st.columns([3, 2])
    with col1:
        order = "total ascending" if seg_type != "age_band" else None
        fig = px.bar(
            summ, x="participants", y="segment", orientation="h",
            color="participants", color_continuous_scale="Blues",
            labels={"participants": "Participants", "segment": ""},
        )
        if order:
            fig.update_layout(yaxis={"categoryorder": order})
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        view = summ.assign(Share=lambda d: d["share"].map(fmt_pct))
        view = view[["segment", "participants", "Share"]]
        view.columns = ["Segment", "Participants", "Share"]
        st.dataframe(view, hide_index=True, use_container_width=True)
    st.divider()
