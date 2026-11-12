"""Data loading and preprocessing for the Global Power Plant Database.

All cleaning decisions are documented in ANALYSIS_NOTES.md ("Cleaning decisions").
The raw CSV is never modified; cleaning happens in memory on load.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "global_power_plant_database.csv"

HOURS_PER_YEAR = 8760
DATA_YEAR = 2020            # database frozen ~2020 (v1.3.0) → reference year for plant age
ACTUAL_YEARS = range(2013, 2020)      # generation_gwh_2013 … 2019 (reported)
ESTIMATED_YEARS = range(2013, 2018)   # estimated_generation_gwh_2013 … 2017 (WRI model)
OTHER_FUELS = ["other_fuel1", "other_fuel2", "other_fuel3"]

# Identifiers, URLs and source notes: not used in any analysis
DROP_COLS = [
    "url", "wepp_id", "gppd_idnr", "geolocation_source",
    "generation_data_source", "year_of_capacity_data",
] + [f"estimated_generation_note_{y}" for y in ESTIMATED_YEARS]

FUEL_GROUP = {
    "Solar": "Renewable", "Wind": "Renewable", "Hydro": "Renewable",
    "Geothermal": "Renewable", "Biomass": "Renewable", "Wave and Tidal": "Renewable",
    "Coal": "Fossil", "Gas": "Fossil", "Oil": "Fossil", "Petcoke": "Fossil", "Cogeneration": "Fossil",
    "Nuclear": "Nuclear",
    "Waste": "Other", "Storage": "Other", "Other": "Other",
}


@st.cache_data
def load_raw() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH, low_memory=False)


def _clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Apply all cleaning steps; return (clean dataframe, summary of what was changed)."""
    report = {"rows_raw": len(df)}
    df = df.drop(columns=[c for c in DROP_COLS if c in df.columns]).copy()

    # 1) Validity checks (raw data passes all of them; kept as safeguards)
    df = df[df["capacity_mw"] > 0]
    df = df.dropna(subset=["latitude", "longitude", "primary_fuel"])

    # 2) Secondary fuels: NaN = "no secondary fuel" (structural missingness, not lost data).
    #    Caveat: mostly reported for US plants; elsewhere NaN may also mean "not reported".
    df["n_fuels"] = 1 + df[OTHER_FUELS].notna().sum(axis=1)
    df["has_secondary_fuel"] = df["n_fuels"] > 1
    df[OTHER_FUELS] = df[OTHER_FUELS].fillna("None")

    # 3) Actual generation: |capacity factor| > 1 is physically impossible → that year's value becomes NaN
    #    (the plant itself is kept: capacity / location / fuel are valid).
    #    CF > 1  : produced more than running at full capacity all year.
    #    CF < -1 : consumed more than its own rating all year (e.g. 1.8 MW plant at -132 GWh → site load mixed in).
    #    Other negative values are KEPT: net consumers (storage, pumped hydro, standby backup plants).
    too_high = too_low = 0
    for y in ACTUAL_YEARS:
        col = f"generation_gwh_{y}"
        cf = df[col] * 1000 / (df["capacity_mw"] * HOURS_PER_YEAR)
        too_high += int((cf > 1).sum())
        too_low += int((cf < -1).sum())
        df.loc[cf.abs() > 1, col] = np.nan
    report["impossible_generation_values"] = too_high + too_low
    report["impossible_cf_above_1"] = too_high
    report["impossible_cf_below_minus_1"] = too_low
    report["negative_generation_2017"] = int((df["generation_gwh_2017"] < 0).sum())

    # 4) Capacity factors — actual and estimated kept SEPARATE (never mixed in one column).
    #    Estimated CF is WRI's own assumption → do not use it as an ML target.
    df["cf_actual_2017"] = df["generation_gwh_2017"] * 1000 / (df["capacity_mw"] * HOURS_PER_YEAR)
    df["cf_estimated_2017"] = df["estimated_generation_gwh_2017"] * 1000 / (df["capacity_mw"] * HOURS_PER_YEAR)

    # 5) Commissioning year: fractional values = capacity-weighted average of units → round.
    #    ~50% missing and NOT random (US 0% vs rest 70%; solar/wind more than coal) → never imputed.
    df["commissioning_year"] = df["commissioning_year"].round()
    df["year_known"] = df["commissioning_year"].notna()
    df["plant_age"] = DATA_YEAR - df["commissioning_year"]

    # 6) Owner: explicit label instead of NaN
    df["owner"] = df["owner"].fillna("Unknown")

    # 7) Derived columns for charts / filters / caveats
    df["fuel_group"] = df["primary_fuel"].map(FUEL_GROUP).fillna("Other")
    df["is_renewable"] = df["fuel_group"] == "Renewable"
    df["is_us"] = df["country"] == "USA"
    df["size_class"] = pd.cut(
        df["capacity_mw"],
        bins=[0, 10, 100, 1000, np.inf],
        labels=["Small (<10 MW)", "Medium (10-100 MW)", "Large (100-1000 MW)", "Very large (>1 GW)"],
    ).astype(str)

    # 8) Capacity outliers: very large plants (e.g. Three Gorges ≈ 22.5 GW) are REAL → kept;
    #    charts use log scales where needed.
    report["rows_clean"] = len(df)
    return df.reset_index(drop=True), report


@st.cache_data
def load_clean() -> pd.DataFrame:
    """Cleaned dataframe used by every chart."""
    return _clean(load_raw())[0]


@st.cache_data
def cleaning_report() -> dict:
    """Counts of what cleaning changed (for the Overview section / README)."""
    return _clean(load_raw())[1]