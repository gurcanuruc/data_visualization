"""CEN445 — Global Power Plants Exploratory Dashboard (main Streamlit app).

Run:  streamlit run app.py
"""
import streamlit as st

from src.data_loader import load_clean, cleaning_report
from src import member1, member2, member3

st.set_page_config(page_title="Global Power Plants Dashboard", page_icon="⚡", layout="wide")

df = load_clean()

# ---------------- Sidebar filters (shared by all charts) ----------------
st.sidebar.header("Filters")

fuels = sorted(df["primary_fuel"].unique())
sel_fuels = st.sidebar.multiselect("Primary fuel", fuels, default=fuels)

countries = ["All"] + sorted(df["country_long"].unique())
sel_country = st.sidebar.selectbox("Country", countries)

cap_min, cap_max = float(df["capacity_mw"].min()), float(df["capacity_mw"].max())
sel_cap = st.sidebar.slider("Capacity (MW)", cap_min, cap_max, (cap_min, cap_max))

only_with_year = st.sidebar.checkbox("Only plants with known commissioning year", value=False)

fdf = df[df["primary_fuel"].isin(sel_fuels) & df["capacity_mw"].between(*sel_cap)]
if sel_country != "All":
    fdf = fdf[fdf["country_long"] == sel_country]
if only_with_year:
    fdf = fdf.dropna(subset=["commissioning_year"])

# ---------------- Header & KPIs ----------------
st.title("⚡ Global Power Plants — Exploratory Dashboard")
st.caption("Data: WRI Global Power Plant Database v1.3.0 (CC BY 4.0)")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Plants", f"{len(fdf):,}")
k2.metric("Countries", fdf["country_long"].nunique())
k3.metric("Total capacity", f"{fdf['capacity_mw'].sum() / 1000:,.0f} GW")
ren_share = fdf.loc[fdf["fuel_group"] == "Renewable", "capacity_mw"].sum() / max(fdf["capacity_mw"].sum(), 1)
k4.metric("Renewable share (capacity)", f"{ren_share:.0%}")

if fdf.empty:
    st.warning("No plants match the current filters.")
    st.stop()

# ---------------- Section navigation ----------------
# st.tabs renders EVERY tab on each rerun; a radio renders only the selected section,
# so heavy charts (e.g. the map) are not rebuilt while working in another section.
section = st.radio("Section", ["Overview & data", "Part 1", "Part 2", "Part 3"],
                   horizontal=True, label_visibility="collapsed")
st.divider()

if section == "Overview & data":
    rep = cleaning_report()
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows after cleaning", f"{rep['rows_clean']:,} / {rep['rows_raw']:,}")
    c2.metric("Impossible generation values → NaN", rep["impossible_generation_values"])
    c3.metric("Net-consumer plants (2017, kept)", rep["negative_generation_2017"])
    st.dataframe(fdf.head(200), width="stretch")
    st.write("Missing values after cleaning (%):")
    st.dataframe((fdf.isna().mean() * 100).round(1).rename("missing %").to_frame().T)
elif section == "Part 1":
    member1.render(fdf)
elif section == "Part 2":
    member2.render(fdf)
else:
    member3.render(fdf)