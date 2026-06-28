"""Generate the bundled **synthetic** NDIS sample dataset.

The numbers here are fabricated but shaped to resemble real NDIS market data:
participant counts, committed supports ($), payments ($), provider counts and
demographic splits across Australian service regions and years.

Run from the project root::

    python scripts/generate_sample_data.py

It writes deterministic CSVs (fixed RNG seed) into ``data/sample/`` so the app
is reproducible and works completely offline. NOTHING here is real NDIS data.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Allow running as a plain script (``python scripts/generate_sample_data.py``).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ndis_explorer.config import (  # noqa: E402
    AGE_BANDS,
    ALL_SUPPORT_CATEGORIES,
    CATEGORY_GROUP,
    DISABILITY_TYPES,
    PLAN_MANAGEMENT_TYPES,
    SAMPLE_DATA_DIR,
)

SEED = 20240627
YEARS = [2020, 2021, 2022, 2023, 2024]

# Plausible service-region names per state. These echo the style of NDIS service
# districts / ABS SA3 regions but are used here purely as labels for fake data.
REGIONS_BY_STATE: dict[str, list[str]] = {
    "NSW": [
        "Sydney Inner City", "Western Sydney", "Northern Sydney",
        "Hunter & Newcastle", "Illawarra Shoalhaven", "Mid North Coast",
        "Murrumbidgee & Far West",
    ],
    "VIC": [
        "Melbourne Inner", "Melbourne North & West", "Melbourne South East",
        "Barwon (Geelong)", "Hume & Goulburn", "Gippsland",
    ],
    "QLD": [
        "Brisbane North", "Brisbane South", "Gold Coast",
        "Sunshine Coast", "Townsville & North QLD", "Central Queensland",
    ],
    "WA": [
        "Perth Metro North", "Perth Metro South", "Peel & South West",
        "Goldfields & Wheatbelt", "Kimberley & Pilbara",
    ],
    "SA": [
        "Adelaide Metro", "Adelaide Hills & Barossa", "Eyre & Far North",
        "Limestone Coast",
    ],
    "TAS": ["Hobart & South", "Launceston & North", "North West Coast"],
    "ACT": ["Canberra Central", "Canberra Outer"],
    "NT": ["Darwin & Top End", "Central Australia (Alice Springs)"],
}

# Remoteness influences provider supply (remote areas are chronically thin on
# providers, creating opportunity but also delivery difficulty).
REMOTENESS_BY_KEYWORD = {
    "Far West": "Remote",
    "Far North": "Remote",
    "Kimberley": "Remote",
    "Pilbara": "Remote",
    "Goldfields": "Remote",
    "Central Australia": "Remote",
    "Top End": "Remote",
    "Eyre": "Remote",
    "Gippsland": "Regional",
    "Mid North Coast": "Regional",
    "Murrumbidgee": "Regional",
    "Hume": "Regional",
    "North West Coast": "Regional",
    "Limestone Coast": "Regional",
    "Wheatbelt": "Remote",
}


def _remoteness(region_name: str) -> str:
    for keyword, level in REMOTENESS_BY_KEYWORD.items():
        if keyword in region_name:
            return level
    # Capital-city / metro names are Major Cities; everything else Regional.
    metro_markers = ("Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide",
                     "Canberra", "Hobart", "Darwin", "Gold Coast", "Metro",
                     "Inner", "Newcastle")
    if any(m in region_name for m in metro_markers):
        return "Major City"
    return "Regional"


def build_regions(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    rid = 1
    for state, names in REGIONS_BY_STATE.items():
        for name in names:
            remoteness = _remoteness(name)
            # Population scaled by remoteness band.
            base = {
                "Major City": (180_000, 900_000),
                "Regional": (60_000, 280_000),
                "Remote": (15_000, 90_000),
            }[remoteness]
            population = int(rng.integers(base[0], base[1]))
            rows.append(
                {
                    "region_id": f"R{rid:03d}",
                    "region_name": name,
                    "state": state,
                    "remoteness": remoteness,
                    "population": population,
                }
            )
            rid += 1
    return pd.DataFrame(rows)


def build_market(regions: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Participants, committed supports and payments per region per year."""
    rows = []
    for _, reg in regions.iterrows():
        # NDIS participation rate ~ 2-3% of population, varying by region.
        participation_rate = rng.uniform(0.018, 0.032)
        base_participants = max(150, int(reg["population"] * participation_rate))

        # Annual participant growth (NDIS has grown fast; taper over time).
        growth_rates = rng.uniform(0.06, 0.18, size=len(YEARS))

        # Average committed supports per participant (~$60k, varies by region;
        # remote regions tend to have higher per-capita plans).
        remote_loading = {"Major City": 1.0, "Regional": 1.08, "Remote": 1.25}[
            reg["remoteness"]
        ]
        avg_committed = rng.uniform(48_000, 78_000) * remote_loading

        # Utilisation (payments / committed). Lower in thin markets => unmet need.
        base_util = {
            "Major City": rng.uniform(0.82, 0.93),
            "Regional": rng.uniform(0.70, 0.86),
            "Remote": rng.uniform(0.55, 0.78),
        }[reg["remoteness"]]

        participants = base_participants
        for i, year in enumerate(YEARS):
            if i > 0:
                participants = int(participants * (1 + growth_rates[i]))
            committed = participants * avg_committed * rng.uniform(0.97, 1.05)
            # Utilisation drifts up slightly over time as markets mature.
            util = min(0.97, base_util + i * 0.012 + rng.uniform(-0.02, 0.02))
            payments = committed * util
            rows.append(
                {
                    "region_id": reg["region_id"],
                    "year": year,
                    "active_participants": participants,
                    "committed_supports": round(committed, 2),
                    "payments": round(payments, 2),
                }
            )
    return pd.DataFrame(rows)


def build_support_categories(
    market: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    """Split each region/year committed + payments across support categories."""
    # Stable-ish share of committed supports per category (sums to ~1).
    base_shares = rng.dirichlet(np.ones(len(ALL_SUPPORT_CATEGORIES)) * 3.0)
    share_map = dict(zip(ALL_SUPPORT_CATEGORIES, base_shares))

    rows = []
    for _, m in market.iterrows():
        # Per-region jitter so category mix differs by region.
        jitter = rng.uniform(0.8, 1.2, size=len(ALL_SUPPORT_CATEGORIES))
        shares = np.array([share_map[c] for c in ALL_SUPPORT_CATEGORIES]) * jitter
        shares = shares / shares.sum()
        for cat, share in zip(ALL_SUPPORT_CATEGORIES, shares):
            committed = m["committed_supports"] * share
            # Category-specific utilisation: Support Coordination & AT tend to be
            # under-utilised in thin markets (proxy for provider scarcity).
            cat_util_mult = {
                "Support Coordination": 0.9,
                "Assistive Technology": 0.88,
                "Home Modifications": 0.8,
                "Finding & Keeping a Job": 0.85,
            }.get(cat, 1.0)
            region_util = m["payments"] / m["committed_supports"]
            util = min(0.98, region_util * cat_util_mult * rng.uniform(0.95, 1.05))
            rows.append(
                {
                    "region_id": m["region_id"],
                    "year": m["year"],
                    "support_category": cat,
                    "budget_group": CATEGORY_GROUP[cat],
                    "committed_supports": round(committed, 2),
                    "payments": round(committed * util, 2),
                }
            )
    return pd.DataFrame(rows)


def build_providers(
    regions: pd.DataFrame, market: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    """Active / registered providers per region per year.

    Provider supply deliberately lags participant demand in regional/remote
    areas, which is exactly the under-servicing signal the model looks for.
    """
    rows = []
    remoteness = regions.set_index("region_id")["remoteness"].to_dict()
    for region_id, grp in market.groupby("region_id"):
        rem = remoteness[region_id]
        # Target participants-per-provider ratio by remoteness (higher = thinner
        # supply). Real-world metro markets are far more crowded.
        target_ratio = {
            "Major City": rng.uniform(8, 16),
            "Regional": rng.uniform(18, 30),
            "Remote": rng.uniform(30, 55),
        }[rem]
        for _, m in grp.sort_values("year").iterrows():
            active = max(3, int(m["active_participants"] / target_ratio))
            active = int(active * rng.uniform(0.9, 1.1))
            registered = int(active * rng.uniform(1.25, 1.7))
            rows.append(
                {
                    "region_id": region_id,
                    "year": m["year"],
                    "active_providers": active,
                    "registered_providers": registered,
                }
            )
    return pd.DataFrame(rows)


def build_demographics(
    market: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    """Latest-year participant breakdown by disability, age and plan management."""
    latest = market[market["year"] == max(YEARS)]
    rows = []

    def _split(total: int, categories, alpha: float = 2.0) -> list[int]:
        shares = rng.dirichlet(np.ones(len(categories)) * alpha)
        counts = np.round(shares * total).astype(int)
        return counts.tolist()

    for _, m in latest.iterrows():
        total = int(m["active_participants"])
        for seg_type, cats in (
            ("disability_type", DISABILITY_TYPES),
            ("age_band", AGE_BANDS),
            ("plan_management", PLAN_MANAGEMENT_TYPES),
        ):
            for cat, count in zip(cats, _split(total, cats)):
                rows.append(
                    {
                        "region_id": m["region_id"],
                        "segment_type": seg_type,
                        "segment": cat,
                        "participants": int(count),
                    }
                )
    return pd.DataFrame(rows)


def main() -> None:
    rng = np.random.default_rng(SEED)
    SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    regions = build_regions(rng)
    market = build_market(regions, rng)
    support = build_support_categories(market, rng)
    providers = build_providers(regions, market, rng)
    demographics = build_demographics(market, rng)

    outputs = {
        "regions.csv": regions,
        "market_by_region_year.csv": market,
        "support_categories_by_region_year.csv": support,
        "providers_by_region_year.csv": providers,
        "demographics_by_region.csv": demographics,
    }
    for filename, df in outputs.items():
        path = SAMPLE_DATA_DIR / filename
        df.to_csv(path, index=False)
        print(f"wrote {path}  ({len(df):,} rows)")


if __name__ == "__main__":
    main()
