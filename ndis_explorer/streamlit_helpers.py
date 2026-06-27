"""Streamlit-specific glue: cached loaders, shared sidebar and formatting.

Kept separate from the pure-analysis modules so the core logic carries no
Streamlit dependency and stays unit-testable.
"""

from __future__ import annotations

import streamlit as st

from .config import APP, DEFAULT_WEIGHTS, STATES, WEIGHT_LABELS, OpportunityWeights
from .data import NdisDataset, load_dataset, resolve_source, user_data_available


# --------------------------------------------------------------------------- #
# Page config
# --------------------------------------------------------------------------- #
def configure_page(title: str, icon: str = "🧭") -> None:
    st.set_page_config(
        page_title=f"{title} - {APP.name}",
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )


# --------------------------------------------------------------------------- #
# Cached data loading
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Loading NDIS data...")
def _cached_load(source: str) -> NdisDataset:
    return load_dataset(source)


def get_dataset() -> NdisDataset:
    """Load the active dataset, honouring a manual source override in session."""
    prefer = st.session_state.get("data_source", "auto")
    source = resolve_source(prefer)
    return _cached_load(source)


def data_source_caption(dataset: NdisDataset) -> None:
    if dataset.source == "user":
        st.caption("Data source: **your uploaded NDIS exports** (`data/user/`).")
    else:
        st.caption(
            "Data source: **bundled synthetic sample** - figures are fabricated "
            "for demonstration. Add real exports via the *Data Manager* page."
        )


# --------------------------------------------------------------------------- #
# Shared sidebar controls
# --------------------------------------------------------------------------- #
def sidebar_data_controls(dataset: NdisDataset) -> None:
    """Common sidebar: source toggle + disclaimer."""
    with st.sidebar:
        st.markdown(f"### {APP.name}")
        st.caption(APP.tagline)
        options = ["auto", "sample"] + (["user"] if user_data_available() else [])
        st.selectbox(
            "Data source",
            options=options,
            key="data_source",
            help=(
                "'auto' uses your uploaded data when present, else the sample. "
                "Upload real exports on the Data Manager page."
            ),
        )
        st.divider()


def weight_controls(key_prefix: str = "w") -> OpportunityWeights:
    """Render opportunity-weight sliders and return the configured weights."""
    with st.sidebar:
        st.markdown("#### Opportunity weights")
        st.caption("Relative importance of each signal (auto-normalised).")
        d = DEFAULT_WEIGHTS.as_dict()
        values = {}
        for field, label in WEIGHT_LABELS.items():
            values[field] = st.slider(
                label,
                min_value=0.0,
                max_value=1.0,
                value=float(d[field]),
                step=0.05,
                key=f"{key_prefix}_{field}",
            )
        if st.button("Reset weights", key=f"{key_prefix}_reset"):
            for field in WEIGHT_LABELS:
                st.session_state[f"{key_prefix}_{field}"] = float(d[field])
            st.rerun()
    return OpportunityWeights(**values)


def region_filter_controls(dataset: NdisDataset) -> tuple[list[str], list[str], int]:
    """Sidebar filters: states, remoteness, year. Returns chosen values."""
    with st.sidebar:
        st.markdown("#### Filters")
        states = st.multiselect(
            "States / territories",
            options=[s for s in STATES if s in dataset.states],
            default=[],
            help="Empty = all states.",
            key="filter_states",
        )
        remoteness_opts = sorted(dataset.regions["remoteness"].unique().tolist())
        remoteness = st.multiselect(
            "Remoteness",
            options=remoteness_opts,
            default=[],
            help="Empty = all remoteness levels.",
            key="filter_remoteness",
        )
        years = dataset.years
        year = st.select_slider(
            "Year",
            options=years,
            value=dataset.latest_year,
            key="filter_year",
        )
    return states, remoteness, year


# --------------------------------------------------------------------------- #
# Formatting
# --------------------------------------------------------------------------- #
def fmt_money(value: float) -> str:
    if value is None or value != value:
        return "n/a"
    for unit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(value) >= unit:
            return f"${value / unit:.2f}{suffix}"
    return f"${value:,.0f}"


def fmt_pct(value: float, digits: int = 1) -> str:
    if value is None or value != value:
        return "n/a"
    return f"{value * 100:.{digits}f}%"
