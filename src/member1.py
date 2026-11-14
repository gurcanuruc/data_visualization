"""
CEN445 - Member1 (Dila) Visualizations
Part 1: Map, Renewable Share Choropleth, and Fuel Treemap
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Semantic color palette for energy sources (shared across charts)
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


@st.cache_data
def _compute_country_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Fast vectorized country aggregation (avoids slow row-wise lambda)."""
    temp = df[["country", "country_long", "capacity_mw", "is_renewable"]].copy()
    temp["ren_mw"] = temp["capacity_mw"].where(temp["is_renewable"], 0.0)

    country_grouped = (
        temp.groupby(["country", "country_long"], as_index=False)
        .agg(
            total_capacity_mw=("capacity_mw", "sum"),
            renewable_capacity_mw=("ren_mw", "sum"),
            plant_count=("capacity_mw", "count")
        )
    )
    country_grouped["renewable_share_pct"] = (
        country_grouped["renewable_capacity_mw"] / country_grouped["total_capacity_mw"] * 100
    ).round(1)
    return country_grouped


@st.fragment
def _render_chart_1(df: pd.DataFrame):
    st.subheader("1. Global Power Plant Distribution")
    st.caption(
        "Bubble size reflects installed capacity (MW), while color indicates primary fuel. "
        "Rendered via WebGL for smooth zooming and panning."
    )

    col_slider, col_style = st.columns([3, 1])
    with col_slider:
        n = len(df)
        if n > 100:
            slider_cap = min(10000, n)
            max_plants = st.slider(
                "Number of plants to display (Top N by capacity)",
                min_value=100,
                max_value=slider_cap,
                value=min(3000, slider_cap),
                step=100,
                help="Capped at 10,000 points to prevent browser freeze. Plants are sorted by capacity."
            )
        else:
            max_plants = n   # small selection (e.g. one country): show every plant, no slider
    with col_style:
        map_style = st.selectbox(
            "Map theme",
            ["carto-positron", "open-street-map", "carto-darkmatter"],
            index=0
        )

    map_df = (
        df.dropna(subset=["latitude", "longitude"])
        .nlargest(max_plants, "capacity_mw")
    )

    fig_map = px.scatter_map(
        map_df,
        lat="latitude",
        lon="longitude",
        color="primary_fuel",
        color_discrete_map=FUEL_COLORS,
        size="capacity_mw",
        hover_name="name",
        custom_data=["country_long", "primary_fuel", "capacity_mw", "commissioning_year"],
        map_style=map_style,
        zoom=1.1,
        opacity=0.80,
        size_max=18,
        height=550
    )

    fig_map.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "Country: %{customdata[0]}<br>"
            "Primary Fuel: <b>%{customdata[1]}</b><br>"
            "Capacity: <b>%{customdata[2]:,.0f} MW</b><br>"
            "Commissioned: %{customdata[3]}<extra></extra>"
        )
    )

    fig_map.update_layout(
        map=dict(
            bounds=dict(west=-179, east=179, south=-60, north=85)  # Prevents infinite horizontal wrapping
        ),
        legend=dict(
            title=dict(text="Primary Fuel  "),
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
            bgcolor="rgba(255,255,255,0.7)"
        ),
        margin=dict(l=0, r=0, t=40, b=0)
    )

    st.plotly_chart(fig_map, width="stretch")


@st.fragment
def _render_chart_2(df: pd.DataFrame):
    st.subheader("2. Renewable Share of Capacity by Country")
    st.caption(
        "Countries colored by the percentage of their installed capacity coming from renewable sources "
        "(Hydro, Wind, Solar, Biomass, Geothermal, Wave & Tidal)."
    )

    min_cap_threshold = st.slider(
        "Minimum Total Capacity Threshold (MW)",
        min_value=0,
        max_value=50000,
        value=5000,
        step=1000,
        help="Filter out small countries (e.g., 100% hydro micro-states) to prevent them from dominating the rankings."
    )

    country_grouped = _compute_country_stats(df)
    filtered_countries = country_grouped[
        country_grouped["total_capacity_mw"] >= min_cap_threshold
    ]

    if filtered_countries.empty:
        st.warning("No countries meet the selected minimum capacity threshold.")
        return

    top_country = filtered_countries.sort_values("renewable_share_pct", ascending=False).iloc[0]
    median_share = filtered_countries["renewable_share_pct"].median()
    m1, m2, m3 = st.columns(3)
    m1.metric("Countries Shown", f"{len(filtered_countries)}")
    m2.metric("Highest Share", f"{top_country['country_long']} ({top_country['renewable_share_pct']:.1f}%)")
    m3.metric("Median Renewable Share", f"{median_share:.1f}%")

    # Lightweight go.Choropleth with flat equirectangular projection for zero-lag hover/pan
    fig_choropleth = go.Figure(
        go.Choropleth(
            locations=filtered_countries["country"],
            locationmode="ISO-3",
            z=filtered_countries["renewable_share_pct"],
            text=filtered_countries["country_long"],
            customdata=filtered_countries[["total_capacity_mw", "renewable_capacity_mw", "plant_count"]],
            colorscale="RdYlGn",
            zmin=0,
            zmax=100,
            marker_line_color="#FFFFFF",
            marker_line_width=0.4,
            colorbar=dict(
                title="Renewable %",
                ticksuffix="%",
                thickness=14,
                len=0.75
            ),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Renewable Share: <b>%{z:.1f}%</b><br>"
                "Renewable Capacity: %{customdata[1]:,.0f} MW<br>"
                "Total Capacity: %{customdata[0]:,.0f} MW<br>"
                "Reported Plants: %{customdata[2]:,}<extra></extra>"
            )
        )
    )

    fig_choropleth.update_layout(
        height=500,
        geo=dict(
            projection_type="equirectangular",
            resolution=110,
            showframe=False,
            showcoastlines=False,
            showland=True,
            landcolor="#F1F5F9",
            showocean=False,
            showcountries=True,
            countrycolor="#E2E8F0",
            lataxis_range=[-58, 85],
            bgcolor="rgba(0,0,0,0)"
        ),
        margin=dict(l=0, r=0, t=10, b=0),
        uirevision="constant"
    )

    st.plotly_chart(fig_choropleth, width="stretch")

    st.warning(
        """
        **Data Reality Check (Coverage Caveat):**  
        The shares shown on this map rely solely on the plants reported in the WRI dataset. 
        For example, **Turkey (#28 at the 5 GW threshold)** appears to have a renewable share of **30%** in this data. However, because 
        many wind and small unlicensed solar plants are missing, the actual share according to 
        official end-of-2019 figures (EMRA/TEİAŞ) is **45.2%**. 
        
        Similarly, wind capacity in countries like **Denmark** is severely underreported. 
        Meanwhile, hydro-dominant countries like **Paraguay** and **Norway** correctly top the list, 
        and Gulf states sit near 0%.
        """
    )


def render(df):
    st.header("Part 1: Global Distribution & Renewable Share")
    _render_chart_1(df)
    st.divider()
    _render_chart_2(df)
    st.divider()

    # ---------------------------------------------------------
    # Chart 3: Country to Fuel Hierarchy (Treemap) - ORIGINAL
    # ---------------------------------------------------------
    st.subheader("3. Country to Fuel Hierarchy (Treemap)")
    st.caption(
        "Click on a country to drill down into its national capacity mix. "
        "Click the top bar to zoom back out."
    )

    tree_df = df.groupby(["country_long", "primary_fuel"], as_index=False).agg(
        capacity_mw=("capacity_mw", "sum"),
        plant_count=("capacity_mw", "count")
    )
    tree_df = tree_df[tree_df["capacity_mw"] > 0]

    fig_treemap = px.treemap(
        tree_df,
        path=[px.Constant("World"), "country_long", "primary_fuel"],
        values="capacity_mw",
        color="primary_fuel",
        color_discrete_map=FUEL_COLORS,
        custom_data=["capacity_mw", "plant_count"],
        height=600
    )

    fig_treemap.update_traces(
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Capacity: <b>%{value:,.0f} MW</b><br>"
            "Share of Parent: %{percentParent:.1%}<extra></extra>"
        ),
        textinfo="label+percent parent"
    )

    fig_treemap.update_layout(
        margin=dict(t=25, l=0, r=0, b=0)
    )

    st.plotly_chart(fig_treemap, width="stretch")