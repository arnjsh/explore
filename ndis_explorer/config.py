"""Central configuration: paths, domain taxonomy and tunable defaults.

Keeping all of the "magic" values in one place makes the rest of the codebase
easy to read and the model easy to re-tune without hunting through modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PACKAGE_ROOT: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = PACKAGE_ROOT.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
SAMPLE_DATA_DIR: Path = DATA_DIR / "sample"
USER_DATA_DIR: Path = DATA_DIR / "user"

# Logical dataset names -> file names. Both the sample and (optional) user
# directories use the same conventions, so loading is interchangeable.
DATASET_FILES: dict[str, str] = {
    "regions": "regions.csv",
    "market": "market_by_region_year.csv",
    "support_categories": "support_categories_by_region_year.csv",
    "providers": "providers_by_region_year.csv",
    "demographics": "demographics_by_region.csv",
}

# --------------------------------------------------------------------------- #
# Domain taxonomy
# --------------------------------------------------------------------------- #
# Australian states / territories.
STATES: tuple[str, ...] = ("NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT")

# NDIS support categories grouped by budget type. This mirrors the structure of
# real NDIS plans (Core / Capacity Building / Capital) at a level useful for
# market analysis. It is intentionally a curated subset, not exhaustive.
SUPPORT_CATEGORIES: dict[str, list[str]] = {
    "Core": [
        "Assistance with Daily Life",
        "Social & Community Participation",
        "Consumables",
        "Transport",
    ],
    "Capacity Building": [
        "Support Coordination",
        "Improved Daily Living",
        "Finding & Keeping a Job",
        "Improved Health & Wellbeing",
    ],
    "Capital": [
        "Assistive Technology",
        "Home Modifications",
    ],
}

# Flat list of all category names (handy for validation / selects).
ALL_SUPPORT_CATEGORIES: list[str] = [
    name for group in SUPPORT_CATEGORIES.values() for name in group
]

# Reverse lookup: category name -> budget group.
CATEGORY_GROUP: dict[str, str] = {
    name: group
    for group, names in SUPPORT_CATEGORIES.items()
    for name in names
}

# Primary disability types tracked for demographic analysis.
DISABILITY_TYPES: tuple[str, ...] = (
    "Autism",
    "Intellectual Disability",
    "Psychosocial Disability",
    "Physical Disability",
    "Sensory / Speech",
    "Neurological",
    "Other",
)

# Plan management types.
PLAN_MANAGEMENT_TYPES: tuple[str, ...] = (
    "Agency Managed",
    "Plan Managed",
    "Self Managed",
)

# Age bands used in the demographics dataset.
AGE_BANDS: tuple[str, ...] = ("0-6", "7-14", "15-24", "25-44", "45-64", "65+")


# --------------------------------------------------------------------------- #
# Opportunity model defaults
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class OpportunityWeights:
    """Weights for the opportunity-scoring model.

    Each component is a normalised 0-100 sub-score (see ``opportunity.py``).
    The final score is a weighted average, so weights only need to be relative
    to one another - they are renormalised before use.
    """

    market_size: float = 0.25      # bigger committed-supports pool = bigger prize
    growth: float = 0.25           # faster participant/funding growth = momentum
    underservice: float = 0.30     # more participants per provider = unmet demand
    utilisation_gap: float = 0.20  # low utilisation = funded-but-unmet need

    def as_dict(self) -> dict[str, float]:
        return {
            "market_size": self.market_size,
            "growth": self.growth,
            "underservice": self.underservice,
            "utilisation_gap": self.utilisation_gap,
        }


# Friendly labels for the weight components (used by the UI).
WEIGHT_LABELS: dict[str, str] = {
    "market_size": "Market size",
    "growth": "Growth momentum",
    "underservice": "Under-servicing (participants per provider)",
    "utilisation_gap": "Utilisation gap (funded but unspent)",
}

DEFAULT_WEIGHTS = OpportunityWeights()


@dataclass(frozen=True)
class AppMeta:
    """Static metadata surfaced in the UI."""

    name: str = "NDIS Opportunity Explorer"
    tagline: str = "Find where Australia needs new disability service providers"
    version: str = "0.1.0"
    disclaimer: str = (
        "For personal research only. The bundled dataset is **synthetic** "
        "(generated, plausible-but-fake numbers) so the app works offline out "
        "of the box. Replace it with real exports from data.ndis.gov.au before "
        "making any real-world decisions."
    )
    data_sources: list[str] = field(
        default_factory=lambda: [
            "NDIS data downloads - https://data.ndis.gov.au",
            "NDIS quarterly reports - https://www.ndis.gov.au/about-us/publications/quarterly-reports",
            "ABS regional population (SA3/SA4) - https://www.abs.gov.au",
        ]
    )


APP = AppMeta()
