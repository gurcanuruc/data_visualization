# Global Power Plants — Exploratory Data Visualization Dashboard

CEN445 Introduction to Data Visualization — Course Assignment (2026-2027 Fall)

An interactive Streamlit dashboard exploring ~35,000 power plants in 167 countries: where they are, what fuels
they use, how they are used in the grid, how the energy mix has changed over time — and **how far the dataset
itself can be trusted**. Findings derived from the data are checked against official statistics; the
contradictions reveal where the dataset is incomplete, which is the main message of the project:
*well-prepared data matters as much as the analysis built on it.*

**Repository:** https://github.com/gurcanuruc/data_visualization

## Team

| Member | Student ID | Contribution |
|---|---|---|
| Dila Okan | 2022555048 | Charts 1-3 (`src/member1.py`): WebGL plant map, renewable-share choropleth with threshold slider and summary metrics, country → fuel treemap; shared fuel color palette |
| Mehmet Ulaş Uslu | 2022555068 | Charts 4-6 (`src/member2.py`): primary → backup fuel Sankey, capacity-factor box plot, commissioning-year timeline with dynamic coverage warning; random-forest capacity-factor regression (ML) |
| Gürcan Uruç | 2022555067 | Exploratory analysis (`notebooks/01_eda.ipynb`), data preprocessing (`src/data_loader.py`), charts 7-10 (`src/member3.py`): estimate-accuracy scatter, K-Means country clustering (map + parallel coordinates), data reality check; project structure & shared sidebar filters |

## Dataset

- **Name:** Global Power Plant Database v1.3.0 (final release; the database is no longer updated by WRI)
- **Source:** World Resources Institute (WRI) — https://datasets.wri.org/dataset/globalpowerplantdatabase
- **Direct CSV:** https://github.com/wri/global-power-plant-database/blob/master/output_database/global_power_plant_database.csv
- **License:** CC BY 4.0
- **Size:** 34,936 rows × 36 columns (included in `data/`) — grid-scale plants (≥ 1 MW), data up to ~2019
- **Key columns:** `country`, `country_long`, `name`, `capacity_mw`, `latitude`, `longitude`, `primary_fuel`,
  `other_fuel1-3`, `commissioning_year`, `owner`, `generation_gwh_2013-2019` (reported),
  `estimated_generation_gwh_2013-2017` (WRI model estimate)

## Preprocessing

All steps are in `src/data_loader.py` (the raw CSV is never modified; cleaning runs in memory and is cached).
The exploratory analysis behind each decision is in `notebooks/01_eda.ipynb` and `ANALYSIS_NOTES.md`.

**Quality checks on the raw data — passed:** no missing capacity, coordinates or fuel; no capacity ≤ 0; no (0, 0)
coordinates; no duplicate plant IDs. Plants sharing the same coordinates and fuel (810) were inspected: they are
mostly phases of one site (e.g. "Rawson I / II"), not duplicates → kept.

| Issue found | Decision | Reason |
|---|---|---|
| `other_fuel1-3` ≈ 94-100% missing | **Kept**, NaN → `"None"`; derived `n_fuels`, `has_secondary_fuel` | NaN means "no secondary fuel" (structural missingness), not lost data. 1,944 plants have a secondary fuel. |
| Capacity factor > 1 (produced more than running at full power all year) | That year's generation value → NaN (200 values, 2013-2019) | Physically impossible → data error. The plant row is kept: capacity, location and fuel are valid. |
| Capacity factor < -1 (consumed more than its own rating all year) | Same rule (7 values) | E.g. a 1.8 MW plant at -132 GWh → site consumption mixed into the plant figure. |
| Other negative generation (2017: 159 plants) | **Kept** | Net electricity consumers: storage / pumped hydro by design, standby backup plants through self-consumption. |
| Reported vs estimated generation | Kept **separate** (`cf_actual_2017`, `cf_estimated_2017`), never mixed | The estimate is WRI's own model output; mixing it with reported data — or using it as an ML target — would just reproduce WRI's assumptions. |
| `commissioning_year` ≈ 50% missing, fractional values (2,060) | Not imputed; rounded; `year_known` and `plant_age` derived | Missingness is not random (see limitations) → imputation would invent history. Fractional years are capacity-weighted averages of multiple units, not errors. |
| `owner` ≈ 40% missing | → `"Unknown"` | Explicit label instead of NaN. |
| Very large plants (e.g. Three Gorges ≈ 22.5 GW) | **Kept** | Real values, not errors → log scales where needed. |
| IDs, URLs, source notes | Dropped | Not used in any analysis. |

Derived columns: `fuel_group` (Renewable / Fossil / Nuclear / Other), `is_renewable`, `is_us`, `size_class`,
`cf_actual_2017`, `cf_estimated_2017`, `plant_age` (reference year 2020).
The *Overview & data* section of the app shows the cleaning summary live.

## Dataset limitations

Checking the data against official statistics showed that its coverage is **uneven, and in a systematic way**:

- **US-heavy in several dimensions.** Reported generation exists for only ~27% of plants (2017: 8,370 of them
  in the US); `commissioning_year` is 0% missing in the US but ~70% elsewhere, so 56% of plants with a known year
  are American; 1,429 of the 1,944 multi-fuel plants are in the US.
- **Missing years are biased by fuel** (solar 67%, wind 58% vs coal 19%) → a "world" timeline understates the
  growth of renewables and mostly tells US history (84% of known-year solar capacity is in the US).
- **Small, distributed wind and solar installations are largely missing.** Large utility-scale fleets are almost
  fully covered (US wind 101%, UK wind 97% of official figures), but Germany wind 8% / solar 14%, Turkey wind 5% /
  solar 12%, Denmark wind ~23% (see chart 10). Consequences: Turkey's renewable share appears as 30% instead of
  the official 45%, and Denmark — a wind-power leader — lands in a coal-dominant K-Means cluster.
- The database stopped being updated around 2019-2020; the most recent years may be incomplete (reporting lag).

These limitations are shown as notes under the affected charts rather than hidden.

## Visualizations

| # | Chart | Type | Insight | Owner |
|---|---|---|---|---|
| 1 | Global plant map | WebGL scatter map ⭐ | The 3,000 largest plants (shown by default) hold 71% of world capacity; large coal and hydro plants concentrate in East Asia, gas in North America and the Middle East. | Dila Okan |
| 2 | Renewable share by country | Choropleth ⭐ | Among countries above 5 GW, hydro countries lead (Paraguay ~100%, Norway 96%) and Gulf states sit near 0%; Turkey ranks #28 (30%), ahead of China, the US and Germany — but see the coverage limitation. | Dila Okan |
| 3 | Country → fuel hierarchy | Treemap ⭐ | China and the US alone hold 46% of the capacity in the data (top 10 countries: 70%), with very different mixes: China and India ~2/3 coal, the US led by gas (45%). | Dila Okan |
| 4 | Primary → backup fuel | Sankey ⭐ | 97% of multi-fuel capacity is fossil; the dominant flows are gas → oil (342 GW) and coal → oil (295 GW): oil is the standard backup fuel. Multi-fuel plants are large (median 105 MW vs 15 MW). | Mehmet Ulaş Uslu |
| 5 | Capacity factor by fuel | Box plot | Output depends on the plant's role in the grid: nuclear runs almost constantly (median 0.84), wind (0.31) and solar (0.19) are low but steady, gas splits into baseload and peaker plants (median 0.09, wide spread), oil ≈ 0 (backup). | Mehmet Ulaş Uslu |
| 6 | New capacity by commissioning year | Area | New investment moved from the gas wave of the early 2000s (peak 2002, 71 GW) to wind (2015) and solar (2016); the chart warns that missing years make it mostly US history. | Mehmet Ulaş Uslu |
| 7 | Estimated vs reported generation | Scatter (log axes) | WRI's estimate is accurate for wind, solar, nuclear and coal (median ratio ≈ 0.93-0.99) but badly overestimates backup plants (oil: plants produce only ~2% of the estimate, gas ~56%) and underestimates waste plants (~30×). | Gürcan Uruç |
| 8 | Countries grouped by energy mix | K-Means → choropleth ⭐ | Four groups: hydro-dominant (Norway, Brazil, Canada…), gas-dominant (Gulf states, Algeria…), coal-dominant (China, India…), mixed (France, Argentina…). Denmark's placement in the coal group exposes the coverage gap. | Gürcan Uruç |
| 9 | What separates the clusters | Parallel coordinates ⭐ | Each cluster is defined by one dominant fuel axis; the mixed cluster spreads over several. | Gürcan Uruç |
| 10 | Data reality check | Bar chart + metrics | Dataset vs official end-2019 capacity: big utility-scale fleets are complete, small distributed wind/solar is mostly missing. | Gürcan Uruç |

⭐ = advanced visualization.

**Interactive components**
- *Sidebar (all charts unless noted):* primary-fuel multiselect, country dropdown, capacity range slider,
  "known commissioning year only" checkbox; section selector.
- *Part 1:* number-of-plants slider (top N by capacity) and map theme selector (chart 1); minimum-capacity
  threshold slider (chart 2); click-to-drill-down (chart 3).
- *Part 2:* top-N fuel-pair slider (chart 4); legend toggling of fuels (charts 5-6).
- *Part 3:* country selector limited to countries with reported generation (chart 7); number of clusters `k`
  slider and minimum-capacity threshold (charts 8-9); country selection by dropdown **or by clicking the map** —
  highlights the country and its cluster on the map and in the parallel coordinates and lists the cluster members;
  axis brushing (chart 9); view toggle % / GW and technology filter (chart 10).
- Hover tooltips, zoom and pan on all Plotly charts.

Charts 7-10 use their own controls and ignore the sidebar filters: clustering one filtered country would be
meaningless, and reported generation exists for only 29 countries.

## Machine learning

**1. K-Means clustering of countries (unsupervised) — Gürcan Uruç**
- *Features:* each country's capacity share per fuel (coal, gas, oil, nuclear, hydro, wind, solar, biomass,
  other — small fuels merged into "other"). Countries below 5 GW total capacity are excluded (adjustable), because
  1-2 plants make their shares meaningless → 74 countries.
- *Choosing k:* the elbow method points to k = 4; the silhouette score is highest at k = 3 (0.38) but almost
  equal at k = 4 (0.36). **k = 4** was chosen because its clusters are clearly interpretable; k = 3 merges
  coal-dominant and mixed countries (China with France). `k` stays adjustable in the app.
- *Reproducibility:* `random_state=42`, `n_init=50` — with fewer restarts the result depended on the row order.
- *Cluster names* are generated from the centroids ("⟨fuel⟩-dominant" if one fuel ≥ 50%, otherwise "Mixed").

**2. Capacity-factor regression (supervised) — Mehmet Ulaş Uslu**
- *Target:* reported 2017 capacity factor (generation ÷ capacity × 8,760 h) — not raw generation, which is almost
  capacity × a constant, and not WRI's estimate, which would only reproduce WRI's assumptions.
- *Features:* fuel type (label-encoded), plant age, capacity, latitude; plants with all values known (~9,000,
  mostly US).
- *Model:* random forest (50 trees, max depth 5), 80/20 train-test split → **test R² ≈ 0.41**.
- *Result:* fuel type explains most of the prediction (importance ≈ 0.77), plant age ≈ 0.10, latitude ≈ 0.07,
  capacity ≈ 0.05 — confirming that a plant's role in the grid, set by its fuel, drives how much it runs.

## Sources for the reality check (chart 10)

- U.S. wind: EIA, *Today in Energy* — https://www.eia.gov/todayinenergy/detail.php?id=42955
- UK wind: BEIS figures via Utility Week — https://staging4.utilityweek.co.uk/offshore-wind-track-overtake-onshore-wind-2020
- Germany wind & solar: Fraunhofer ISE — https://www.ise.fraunhofer.de/en/press-media/news/2019/Public-net-electricity-generation-in-germany-2019.html
- Denmark wind: Wind Denmark via NS Energy — https://www.nsenergybusiness.com/?p=242875
- Turkey wind: TÜREB 2019 report via Hürriyet Daily News — https://hurriyetdailynews.com/turkey-adds-687-megawatts-of-installed-wind-capacity-in-2019-153293
- Turkey solar: TEİAŞ via TaiyangNews — https://taiyangnews.info/markets/turkey-close-to-6-gw-installed-solar-power
- Turkey renewable share: EMRA Electricity Market Report 2019 via Daily Sabah — https://www.dailysabah.com/business/energy/turkeys-share-of-installed-renewable-capacity-over-45-in-2019/amp

## Setup

```bash
git clone https://github.com/gurcanuruc/data_visualization.git
cd data_visualization
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Project structure

```
├── app.py                 # main Streamlit app (sidebar filters, KPIs, section selector)
├── src/
│   ├── data_loader.py     # loading + preprocessing (cached)
│   ├── member1.py         # charts 1-3
│   ├── member2.py         # charts 4-6 (+ regression)
│   └── member3.py         # charts 7-10 (+ K-Means)
├── data/global_power_plant_database.csv
├── notebooks/01_eda.ipynb # exploratory data analysis
├── ANALYSIS_NOTES.md      # EDA findings and decisions log
└── requirements.txt
```