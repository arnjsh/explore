"""Data Manager - swap the synthetic sample for real NDIS exports."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ndis_explorer.config import APP, DATASET_FILES, USER_DATA_DIR
from ndis_explorer.data import (
    REQUIRED_COLUMNS,
    DataValidationError,
    load_dataset,
    user_data_available,
)
from ndis_explorer.streamlit_helpers import (
    configure_page,
    get_dataset,
    sidebar_data_controls,
)

configure_page("Data Manager", icon="📁")
dataset = get_dataset()
sidebar_data_controls(dataset)

st.title("📁 Data Manager")
st.markdown(
    "This app ships with **synthetic sample data** so it runs offline. To analyse "
    "the real market, drop in exports from "
    "[data.ndis.gov.au](https://data.ndis.gov.au) shaped to the schemas below "
    "(or upload them here). Files are stored locally in `data/user/` and never "
    "leave your machine."
)

st.info(APP.disclaimer, icon="ℹ️")

# --- Current status ---------------------------------------------------- #
st.subheader("Status")
if user_data_available():
    st.success("A complete set of user data is present in `data/user/`.", icon="✅")
else:
    st.warning("Using bundled sample data. Upload all 5 files to switch.", icon="📦")

# --- Required schemas + sample templates ------------------------------- #
st.subheader("Required files & columns")
for name, filename in DATASET_FILES.items():
    with st.expander(f"`{filename}`  -  required columns"):
        cols = sorted(REQUIRED_COLUMNS[name])
        st.code(", ".join(cols), language="text")
        # Offer the sample file as a template to copy the structure.
        try:
            sample = load_dataset("sample")
            df = getattr(sample, name)
            st.caption("Sample (first rows) — use as a template:")
            st.dataframe(df.head(5), hide_index=True, use_container_width=True)
            st.download_button(
                f"Download sample {filename}",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name=filename,
                mime="text/csv",
                key=f"dl_{name}",
            )
        except Exception:
            pass

st.divider()

# --- Upload ------------------------------------------------------------ #
st.subheader("Upload real exports")
st.caption("Upload one or more of the required CSVs. They are validated on save.")
uploads = st.file_uploader(
    "Drop CSV files here",
    type=["csv"],
    accept_multiple_files=True,
)

filename_to_dataset = {fn: name for name, fn in DATASET_FILES.items()}

if uploads:
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for up in uploads:
        if up.name not in filename_to_dataset:
            st.error(
                f"`{up.name}` is not a recognised file name. Expected one of: "
                f"{', '.join(DATASET_FILES.values())}."
            )
            continue
        try:
            df = pd.read_csv(up)
            required = REQUIRED_COLUMNS[filename_to_dataset[up.name]]
            missing = required - set(df.columns)
            if missing:
                st.error(f"`{up.name}` missing columns: {sorted(missing)}")
                continue
            (USER_DATA_DIR / up.name).write_bytes(up.getvalue())
            st.success(f"Saved `{up.name}` ({len(df):,} rows).")
        except Exception as exc:  # pragma: no cover - UI feedback path
            st.error(f"Could not read `{up.name}`: {exc}")
    st.cache_data.clear()

# --- Validate / reset -------------------------------------------------- #
col1, col2 = st.columns(2)
with col1:
    if st.button("Validate user data"):
        try:
            ds = load_dataset("user")
            st.success(
                f"Valid. {len(ds.regions)} regions, years {ds.years}.", icon="✅"
            )
        except DataValidationError as exc:
            st.error(str(exc))
with col2:
    if st.button("Clear user data (revert to sample)"):
        removed = 0
        for fn in DATASET_FILES.values():
            path = USER_DATA_DIR / fn
            if path.exists():
                path.unlink()
                removed += 1
        st.cache_data.clear()
        st.success(f"Removed {removed} file(s). Now using sample data.")
        st.rerun()
