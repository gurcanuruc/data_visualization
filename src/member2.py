"""Member 2 — visualizations 4-6.

Each function receives the FILTERED dataframe and draws one chart with st.plotly_chart.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# Consistent semantic color palette across the dashboard
FUEL_COLORS = {
    "Coal": "#374151",           # Dark Slate / Charcoal
    "Gas": "#F97316",            # Orange
    "Oil": "#991B1B",            # Dark Red
    "Nuclear": "#8B5CF6",        # Purple
    "Hydro": "#0284C7",          # Ocean Blue
    "Wind": "#06B6D4",           # Cyan / Sky
    "Solar": "#EAB308",          # Golden Yellow
    "Biomass": "#16A34A",        # Forest Green
    "Waste": "#78716C",          # Warm Gray
    "Geothermal": "#DC2626",     # Crimson
    "Storage": "#EC4899",        # Pink
    "Cogeneration": "#6366F1",   # Indigo
    "Petcoke": "#1F2937",        # Near Black
    "Wave and Tidal": "#0EA5E9", # Light Blue
    "Other": "#9CA3AF"           # Neutral Gray
}


def _hex_to_rgba(hex_color: str, alpha: float = 0.4) -> str:
    """Convert hex color to rgba string for translucent Sankey links."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"
    return f"rgba(156, 163, 175, {alpha})"


def chart_4(df):
    st.subheader("4. Primary to Secondary Fuel Flow (Sankey)")
    st.caption(
        "Insight: Multi-fuel plants are mostly fossil-based and use oil/gas as a backup fuel. "
        "Adjust the slider to filter out minor flows and focus on the dominant fuel pairs."
    )

    # Filter plants that only have a secondary fuel (not "None")
    mdf = df[df["has_secondary_fuel"]].copy()
    mdf = mdf[mdf["other_fuel1"] != "None"]

    if mdf.empty:
        st.warning("No multi-fuel plants found for the current filters.")
        return

    # Prepare flow data (Sum of capacity and plant count for Primary Fuel -> Secondary Fuel 1)
    flow = (
        mdf.groupby(["primary_fuel", "other_fuel1"], as_index=False)
        .agg(
            capacity_mw=("capacity_mw", "sum"),
            plant_count=("capacity_mw", "count")
        )
        .sort_values("capacity_mw", ascending=False)
    )

    total_pairs = len(flow)
    if total_pairs > 5:
        top_n = st.slider(
            "Number of top fuel-pair flows to display (by capacity)",
            min_value=5,
            max_value=total_pairs,
            value=min(12, total_pairs),
            step=1,
            help="Hiding tiny fuel pairs removes visual clutter and makes the main flows much easier to read."
        )
        flow = flow.head(top_n).copy()

    # Separate primary and backup labels to prevent cyclic loops in Sankey
    flow["src_label"] = flow["primary_fuel"] + " (Primary)"
    flow["tgt_label"] = flow["other_fuel1"] + " (Backup)"

    src_nodes = list(flow["src_label"].unique())
    tgt_nodes = list(flow["tgt_label"].unique())
    all_nodes = src_nodes + tgt_nodes
    node_dict = {node: i for i, node in enumerate(all_nodes)}

    flow["source"] = flow["src_label"].map(node_dict)
    flow["target"] = flow["tgt_label"].map(node_dict)

    # Map colors to nodes and translucent colors to links based on primary fuel
    node_colors = [
        FUEL_COLORS.get(node.replace(" (Primary)", "").replace(" (Backup)", ""), "#9CA3AF")
        for node in all_nodes
    ]
    link_colors = [
        _hex_to_rgba(FUEL_COLORS.get(pf, "#9CA3AF"), alpha=0.42)
        for pf in flow["primary_fuel"]
    ]

    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=26,              # Generous vertical spacing between nodes
            thickness=24,        # Wider node bars
            line=dict(color="#1E293B", width=0.8),
            label=all_nodes,
            color=node_colors,
            hovertemplate="<b>%{label}</b><br>Total Flow: %{value:,.0f} MW<extra></extra>"
        ),
        link=dict(
            source=flow["source"],
            target=flow["target"],
            value=flow["capacity_mw"],
            color=link_colors,
            customdata=flow["plant_count"],
            hovertemplate=(
                "<b>%{source.label} → %{target.label}</b><br>"
                "Capacity: <b>%{value:,.0f} MW</b><br>"
                "Plants: %{customdata:,}<extra></extra>"
            )
        )
    )])

    fig.update_layout(
        title_text=f"Capacity Flow (MW): Primary Fuel to Backup Fuel (Top {len(flow)} Pairs)",
        font=dict(size=13),
        height=680,              # Expanded vertical height so nodes breathe
        margin=dict(l=20, r=20, t=50, b=30)
    )
    st.plotly_chart(fig, width="stretch")


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
        color_discrete_map=FUEL_COLORS,
        title="Actual Capacity Factor Distribution (2017)",
        labels={"cf_actual_2017": "Capacity Factor", "primary_fuel": "Primary Fuel"},
        height=520
    )
    st.plotly_chart(fig, width="stretch")


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

    # Train/test split to evaluate model accuracy
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Fast and lightweight Random Forest Model
    rf = RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42)
    rf.fit(X_train, y_train)
    test_r2 = rf.score(X_test, y_test)

    st.metric("Test R² Score (80/20 Train-Test Split)", f"{test_r2:.2f}")

    importance = pd.DataFrame({
        "Feature": ["Fuel Type", "Plant Age", "Capacity (MW)", "Latitude"],
        "Importance": rf.feature_importances_
    }).sort_values(by="Importance", ascending=True)

    fig = px.bar(
        importance,
        x="Importance",
        y="Feature",
        orientation="h",
        title="Random Forest Feature Importance (Target: cf_actual_2017)",
        height=380
    )
    st.plotly_chart(fig, width="stretch")


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
        st.warning(
            f"⚠️ **Data Coverage Warning:** **{missing_pct:.1f}% of the selected plants lack commissioning year data**. "
            "Since this chart ignores missing years, the time series might be misleading (especially for solar and wind, where missing data rates are high, this chart mostly reflects US history)."
        )

    # Group capacities by year and primary fuel
    df_grouped = df_year.groupby(["commissioning_year", "primary_fuel"])["capacity_mw"].sum().reset_index()

    fig = px.area(
        df_grouped,
        x="commissioning_year",
        y="capacity_mw",
        color="primary_fuel",
        color_discrete_map=FUEL_COLORS,
        title="Newly Added Plant Capacity over the Years",
        labels={"capacity_mw": "Added Capacity (MW)", "commissioning_year": "Commissioning Year"},
        height=520
    )
    st.plotly_chart(fig, width="stretch")


def render(df):
    chart_4(df)
    st.divider()
    chart_5(df)
    chart_5b(df)
    st.divider()
    chart_6(df)