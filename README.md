# Global Power Plants — Exploratory Data Visualization Dashboard

CEN445 Introduction to Data Visualization — Course Assignment (2026-2027 Fall)

An interactive Streamlit dashboard exploring ~35,000 power plants in 167 countries:
where they are, what fuels they use, how big they are, and how the energy mix has changed over time.

**Live demo:** _TODO (optional: Streamlit Community Cloud link)_

## Team

| Member | Student ID | Contribution |
|---|---|---|
| Member 1 | _ID_ | _e.g. data preprocessing, charts 1-3 (map, Sankey, …)_ |
| Member 2 | _ID_ | _charts 4-6, …_ |
| Member 3 | _ID_ | _charts 7-9, ML (clustering / regression), …_ |

## Dataset

- **Name:** Global Power Plant Database v1.3.0
- **Source:** World Resources Institute (WRI) — https://datasets.wri.org/dataset/globalpowerplantdatabase
- **Direct CSV:** https://github.com/wri/global-power-plant-database/blob/master/output_database/global_power_plant_database.csv
- **License:** CC BY 4.0
- **Size:** 34,936 rows × 36 columns (included in `data/`)
- **Key columns:** `country_long`, `name`, `capacity_mw`, `latitude`, `longitude`, `primary_fuel`,
  `commissioning_year`, `owner`, `generation_gwh_2013-2019`, `estimated_generation_gwh_2013-2017`

## Preprocessing

_TODO — document every decision. Current steps in `src/data_loader.py`:_
- Dropped near-empty / irrelevant columns (`other_fuel1-3` ≈ 94-100% missing, URLs, IDs, notes)
- Removed plants with capacity ≤ 0
- `owner` missing (~40%) → `"Unknown"`
- `commissioning_year` missing (~50%) → kept as missing; time-based charts use only known years
- `generation_gwh` = actual 2019 generation, else estimated 2017 generation (actual values are 72-82% missing)
- Derived: `capacity_factor`, `fuel_group` (Renewable / Fossil / Nuclear / Other), `size_class`
- Outliers: _TODO_

## Visualizations

| # | Chart | Type | Insight | Owner |
|---|---|---|---|---|
| 1 | Global plant map | Scatter geo map | _TODO_ | Member 1 |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |
| 6 | | | | |
| 7 | | | | |
| 8 | | | | |
| 9 | | | | |

**Interactive components:** fuel multiselect, country dropdown, capacity slider, commissioning-year checkbox
(+ hover tooltips, zoom/pan on all Plotly charts).

## Machine learning

_TODO — e.g. K-Means clustering of countries by energy mix; regression of generation from capacity, fuel and age._

## Setup

```bash
git clone https://github.com/<user>/<repo>.git
cd <repo>
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Project structure

```
├── app.py              # main Streamlit app (filters, layout, tabs)
├── src/
│   ├── data_loader.py  # loading + preprocessing (cached)
│   ├── member1.py      # charts 1-3
│   ├── member2.py      # charts 4-6
│   └── member3.py      # charts 7-9
├── data/global_power_plant_database.csv
├── notebooks/          # EDA notebooks
└── requirements.txt
```
