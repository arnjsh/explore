# NDIS Opportunity Explorer

A **local-first** desktop/web application for analysing the Australian **NDIS**
(National Disability Insurance Scheme) market and identifying **where a new
disability service provider could win**.

> ⚠️ **For personal research only.** The app ships with a **synthetic** sample
> dataset (fabricated but realistically shaped numbers) so it runs offline out
> of the box. Replace it with real exports from
> [data.ndis.gov.au](https://data.ndis.gov.au) before making any real-world
> decisions. Nothing in the bundled data is real.

It is intentionally simple: a single Python codebase, plain-CSV data, a
[Streamlit](https://streamlit.io) UI, and a transparent scoring model. No
database, no cloud, no enterprise scaffolding — just clone, install and run.

---

## What it does

The core idea: a strong opening for a new provider combines **funded demand**,
**growth**, **thin provider supply** and a **utilisation gap** (money that is
committed but not being spent). The app quantifies all four and rolls them into
a single, tunable **opportunity score** per service region.

### Pages

| Page | What you get |
| --- | --- |
| 🧭 **Home** | Headline market figures and a guided tour |
| 📊 **Market Overview** | National & state size, growth and utilisation trends |
| 🎯 **Opportunity Finder** | Regions ranked by a weighted, explainable score |
| 🗺️ **Regional Explorer** | Deep-dive into a single region (history + demographics) |
| 🧩 **Support Categories** | Which services have unmet, growing demand |
| 👥 **Demographics** | Participant mix by disability, age and plan management |
| 🤖 **AI Insights** | Auto-written briefs grounded in the computed metrics |
| 📁 **Data Manager** | Swap the sample for real NDIS exports |

---

## Quick start

```bash
# 1. (Optional) create a virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Re)generate the synthetic sample data — already committed, but reproducible
python scripts/generate_sample_data.py

# 4. Run the app
streamlit run streamlit_app.py
```

Then open the URL Streamlit prints (default <http://localhost:8501>).

---

## The opportunity model

The model lives in [`ndis_explorer/opportunity.py`](ndis_explorer/opportunity.py)
and is deliberately transparent. Each region gets four **0–100 sub-scores**
(percentile-ranked against the peer group you've filtered to):

| Sub-score | Metric | Why it matters |
| --- | --- | --- |
| **Market size** | Committed supports ($) | The size of the prize |
| **Growth** | Participant CAGR | Demand momentum |
| **Under-servicing** | Participants per active provider | Thin supply = room to enter |
| **Utilisation gap** | `1 − payments/committed` | Funded need going unmet |

The final score is a **weighted average** of the four. Weights are fully
tunable from the sidebar (and auto-normalised), so you can match the model to
your strategy — e.g. weight *under-servicing* heavily if you want to chase
under-served regional/remote markets.

---

## Data model

Five plain CSVs (see [`scripts/generate_sample_data.py`](scripts/generate_sample_data.py)
for the exact shapes). Sample data lives in `data/sample/`; your real exports go
in `data/user/` (git-ignored, private) and automatically take precedence.

| File | Grain | Key columns |
| --- | --- | --- |
| `regions.csv` | region | `region_id, region_name, state, remoteness, population` |
| `market_by_region_year.csv` | region × year | `active_participants, committed_supports, payments` |
| `support_categories_by_region_year.csv` | region × year × category | `support_category, budget_group, committed_supports, payments` |
| `providers_by_region_year.csv` | region × year | `active_providers, registered_providers` |
| `demographics_by_region.csv` | region × segment | `segment_type, segment, participants` |

### Using real NDIS data

1. Download datasets from [data.ndis.gov.au](https://data.ndis.gov.au) (and ABS
   regional population if you want participation rates).
2. Reshape them to match the schemas above (the **Data Manager** page lets you
   download each sample file as a template).
3. Drop the CSVs into `data/user/` (or upload them on the Data Manager page).

The app validates columns on load and falls back to the sample if anything is
missing.

---

## AI insights (optional)

The **AI Insights** page (and the briefs on other pages) work with **zero
configuration** via a built-in deterministic, rule-based writer.

To enable LLM-written briefs instead:

```bash
pip install openai          # already in requirements.txt
export OPENAI_API_KEY=sk-...
# optional: export NDIS_LLM_MODEL=gpt-4o-mini
streamlit run streamlit_app.py
```

The LLM is only ever given the **facts the app computes** as grounding — it
summarises, it does not invent numbers — and any failure transparently falls
back to the rule-based writer.

---

## Project layout

```
.
├── streamlit_app.py            # Home / entry point
├── pages/                      # Streamlit multipage UI
├── ndis_explorer/              # Pure, testable core logic
│   ├── config.py               # Paths, taxonomy, model defaults
│   ├── data.py                 # Loading & validation
│   ├── analysis.py             # Market sizing, growth, metrics
│   ├── opportunity.py          # The scoring model
│   ├── ai.py                   # Insight generation (LLM optional)
│   └── streamlit_helpers.py    # UI glue (cached loaders, sidebar)
├── data/sample/                # Synthetic sample CSVs (tracked)
├── data/user/                  # Your real exports (git-ignored)
├── scripts/generate_sample_data.py
├── tests/                      # pytest suite (logic + page smoke tests)
├── requirements.txt
└── pyproject.toml
```

---

## Development

```bash
pip install -r requirements.txt
pytest                 # runs unit tests + Streamlit page smoke tests
```

The core logic in `ndis_explorer/` carries **no Streamlit dependency**, so it is
straightforward to unit-test. The page smoke tests use Streamlit's `AppTest`
harness to execute every page headlessly and assert it renders without error.

---

## Design principles

- **Simplicity over scale** — one language, flat CSVs, no services to run.
- **Transparency** — the model is a readable weighted average, not a black box.
- **Honesty** — synthetic data is clearly labelled; the LLM is grounded in real
  computed figures.
- **Rapid iteration** — change a weight, a metric or a dataset and re-run.

## License

MIT — for personal, non-commercial research use.
