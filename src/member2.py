"""Member 2 — visualizations 4-6.

Each function receives the FILTERED dataframe and draws one chart with st.plotly_chart.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder

def chart_4(df):
    st.subheader("4. Primary to Secondary Fuel Flow (Sankey)")
    st.caption("Insight: Multi-fuel plants are mostly fossil-based and use oil/gas as a backup fuel.")
    
    # Filter plants that only have a secondary fuel (not "None")
    mdf = df[df["has_secondary_fuel"]].copy()
    mdf = mdf[mdf["other_fuel1"] != "None"]
    
    if mdf.empty:
        st.warning("No multi-fuel plants found for the current filters.")
        return

    # Prepare flow data (Sum of capacity for Primary Fuel -> Secondary Fuel 1)
    flow = mdf.groupby(["primary_fuel", "other_fuel1"])["capacity_mw"].sum().reset_index()

    # Convert labels to indices for the Sankey diagram (Plotly go.Sankey requirement)
    all_nodes = list(pd.concat([flow["primary_fuel"], flow["other_fuel1"]]).unique())
    node_dict = {node: i for i, node in enumerate(all_nodes)}

    flow["source"] = flow["primary_fuel"].map(node_dict)
    flow["target"] = flow["other_fuel1"].map(node_dict)

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=all_nodes
        ),
        link=dict(
            source=flow["source"],
            target=flow["target"],
            value=flow["capacity_mw"]
        )
    )])
    fig.update_layout(title_text="Capacity Flow (MW): Primary Fuel to Backup Fuel", font_size=12)
    st.plotly_chart(fig, use_container_width=True)

def chart_5(df):
    st.subheader("5. Capacity Factor by Fuel Type")
    st.caption("Note: The capacity factor chart is based on plants with known generation data (mostly US). It indicates the plant's role in the grid (baseload, weather-dependent, or backup/peaker).")
    
    df_cf = df.dropna(subset=["cf_actual_2017"]).copy()
    if df_cf.empty:
        st.warning("No 'cf_actual_2017' (Capacity Factor) data available for this selection.")
        return

    fig = px.box(
        df_cf, 
        x="primary_fuel", 
        y="cf_actual_2017", 
        color="primary_fuel",
        title="Actual Capacity Factor Distribution (2017)",
        labels={"cf_actual_2017": "Capacity Factor", "primary_fuel": "Primary Fuel"}
    )
    st.plotly_chart(fig, use_container_width=True)

def chart_5b(df):
    st.subheader("5b. What Drives the Capacity Factor? (Machine Learning)")
    
    # Keep rows without NaN in the required columns for regression
    req_cols = ["cf_actual_2017", "plant_age", "capacity_mw", "latitude", "primary_fuel"]
    df_ml = df.dropna(subset=req_cols).copy()
    
    if len(df_ml) < 50:
        st.info("Not enough data (minimum 50 records) to train a reliable machine learning regression model.")
        return

    # Encode categorical data (primary_fuel) to numeric format
    le = LabelEncoder()
    df_ml["fuel_encoded"] = le.fit_transform(df_ml["primary_fuel"])

    X = df_ml[["fuel_encoded", "plant_age", "capacity_mw", "latitude"]]
    y = df_ml["cf_actual_2017"]

    # Fast and lightweight Random Forest Model
    rf = RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42)
    rf.fit(X, y)

    importance = pd.DataFrame({
        "Feature": ["Fuel Type", "Plant Age", "Capacity (MW)", "Latitude"],
        "Importance": rf.feature_importances_
    }).sort_values(by="Importance", ascending=True)

    fig = px.bar(
        importance, 
        x="Importance", 
        y="Feature", 
        orientation='h',
        title="Random Forest Feature Importance (Target: cf_actual_2017)"
    )
    st.plotly_chart(fig, use_container_width=True)

def chart_6(df):
    st.subheader("6. New Capacity by Commissioning Year")
    
    total_plants = len(df)
    df_year = df.dropna(subset=["commissioning_year"]).copy()
    known_plants = len(df_year)

    if known_plants == 0:
        st.warning("No plants with a known commissioning year for the current filters.")
        return

    # Dynamic Missing Data Warning (Requirement from ANALYSIS_NOTES.md -> Insight 4)
    missing_pct = (1 - known_plants / max(total_plants, 1)) * 100
    if missing_pct > 0:
        st.warning(f"⚠️ **Data Coverage Warning:** **{missing_pct:.1f}% of the selected plants lack commissioning year data**. " 
                   "Since this chart ignores missing years, the time series might be misleading (especially for solar and wind, where missing data rates are high, this chart mostly reflects US history).")

    # Group capacities by year and primary fuel
    df_grouped = df_year.groupby(["commissioning_year", "primary_fuel"])["capacity_mw"].sum().reset_index()

    fig = px.area(
        df_grouped, 
        x="commissioning_year", 
        y="capacity_mw", 
        color="primary_fuel",
        title="Newly Added Plant Capacity over the Years",
        labels={"capacity_mw": "Added Capacity (MW)", "commissioning_year": "Commissioning Year"}
    )
    st.plotly_chart(fig, use_container_width=True)

def render(df):
    chart_4(df)
    st.divider()
    chart_5(df)
    chart_5b(df)
    st.divider()
    chart_6(df)