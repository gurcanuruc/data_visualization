"""
CEN445 - Member 1 (Dila) Visualizations
Part 1: Map, Renewable Share Choropleth, and Fuel Treemap
"""
import streamlit as st
import plotly.express as px
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


def render(df):
    st.header("Part 1: Global Distribution & Renewable Share")

    # ---------------------------------------------------------
    # Chart 1: Global Plant Map (Scatter Geo)
    # ---------------------------------------------------------
    st.subheader("1. Global Power Plant Distribution")
    st.caption(
        "Bubble size reflects installed capacity (MW), while color indicates primary fuel. "
        "Use the slider to control how many of the largest plants are rendered."
    )

    col_slider, col_proj = st.columns([3, 1])
    with col_slider:
        max_plants = st.slider(
            "Number of plants to display (Top N by capacity)",
            min_value=100,
            max_value=len(df) if len(df) > 100 else 1000,
            value=min(5000, len(df)),
            step=500,
            help="Limiting the number of points improves rendering speed. Plants are sorted by capacity."
        )
    with col_proj:
        projection = st.selectbox(
            "Map projection",
            ["natural earth", "equirectangular", "orthographic"],
            index=0
        )

    # Sort by capacity and take top N
    map_df = (
        df.dropna(subset=["latitude", "longitude"])
        .sort_values(by="capacity_mw", ascending=False)
        .head(max_plants)
    )

    fig_map = px.scatter_geo(
        map_df,
        lat="latitude",
        lon="longitude",
        color="primary_fuel",
        color_discrete_map=FUEL_COLORS,
        size="capacity_mw",
        hover_name="name",
        custom_data=["country_long", "primary_fuel", "capacity_mw", "commissioning_year"],
        projection=projection,
        opacity=0.78,
        size_max=22,
        height=600
    )

    # Clean, custom hover tooltip & crisp bubble borders
    fig_map.update_traces(
        marker=dict(line=dict(width=0.5, color="rgba(255, 255, 255, 0.65)")),
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "Country: %{customdata[0]}<br>"
            "Primary Fuel: <b>%{customdata[1]}</b><br>"
            "Capacity: <b>%{customdata[2]:,.0f} MW</b><br>"
            "Commissioned: %{customdata[3]}<extra></extra>"
        )
    )

    fig_map.update_layout(
        geo=dict(
            showframe=False,
            showcoastlines=True,
            coastlinecolor="#CBD5E1",
            showland=True,
            landcolor="#F8FAFC",
            showocean=True,
            oceancolor="#E0F2FE",
            showcountries=True,
            countrycolor="#E2E8F0",
            bgcolor="rgba(0,0,0,0)"
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

    st.plotly_chart(fig_map, use_container_width=True)

    st.divider()

    # ---------------------------------------------------------
    # Chart 2: Renewable Share by Country (Choropleth)
    # ---------------------------------------------------------
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

    # Calculate total, renewable capacity, and plant count per country
    country_grouped = (
        df.groupby("country_long", as_index=False)
        .agg(
            total_capacity_mw=("capacity_mw", "sum"),
            renewable_capacity_mw=(
                "capacity_mw",
                lambda s: s[df.loc[s.index, "fuel_group"] == "Renewable"].sum()
            ),
            plant_count=("capacity_mw", "count")
        )
    )
    country_grouped["renewable_share_pct"] = (
        country_grouped["renewable_capacity_mw"] / country_grouped["total_capacity_mw"] * 100
    )

    filtered_countries = country_grouped[
        country_grouped["total_capacity_mw"] >= min_cap_threshold
    ].copy()

    # Quick summary metrics above the map
    if not filtered_countries.empty:
        top_country = filtered_countries.sort_values("renewable_share_pct", ascending=False).iloc[0]
        median_share = filtered_countries["renewable_share_pct"].median()
        m1, m2, m3 = st.columns(3)
        m1.metric("Countries Shown", f"{len(filtered_countries)}")
        m2.metric("Highest Share", f"{top_country['country_long']} ({top_country['renewable_share_pct']:.1f}%)")
        m3.metric("Median Renewable Share", f"{median_share:.1f}%")

    fig_choropleth = px.choropleth(
        filtered_countries,
        locations="country_long",
        locationmode="country names",
        color="renewable_share_pct",
        hover_name="country_long",
        custom_data=["renewable_share_pct", "total_capacity_mw", "renewable_capacity_mw", "plant_count"],
        color_continuous_scale="RdYlGn",   # Red (0% fossil-heavy) -> Yellow -> Green (100% renewable)
        range_color=[0, 100],
        projection="natural earth",
        height=560
    )

    fig_choropleth.update_traces(
        marker_line_width=0.6,
        marker_line_color="#FFFFFF",
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "Renewable Share: <b>%{customdata[0]:.1f}%</b><br>"
            "Renewable Capacity: %{customdata[2]:,.0f} MW<br>"
            "Total Capacity: %{customdata[1]:,.0f} MW<br>"
            "Reported Plants: %{customdata[3]:,}<extra></extra>"
        )
    )

    fig_choropleth.update_layout(
        geo=dict(
            showframe=False,
            showcoastlines=True,
            coastlinecolor="#CBD5E1",
            showland=True,
            landcolor="#F1F5F9",       # Excluded countries appear in subtle light gray
            showocean=True,
            oceancolor="#F8FAFC",
            showcountries=True,
            countrycolor="#E2E8F0",
            lataxis_range=[-58, 85],   # Crop out Antarctica for a larger, cleaner view
            bgcolor="rgba(0,0,0,0)"
        ),
        coloraxis_colorbar=dict(
            title="Renewable %",
            ticksuffix="%",
            thickness=16,
            len=0.75
        ),
        margin=dict(l=0, r=0, t=20, b=0)
    )

    st.plotly_chart(fig_choropleth, use_container_width=True)

    # Presentation Theme: Data Reality Check (Coverage Caveat)
    st.warning(
        """
        **Data Reality Check (Coverage Caveat):**  
        The shares shown on this map rely solely on the plants reported in the WRI dataset. 
        For example, **Turkey (#28)** appears to have a renewable share of **30%** in this data. However, because 
        many wind and small unlicensed solar plants are missing, the actual share according to 
        official end-of-2019 figures (EMRA/TEİAŞ) is **45.2%**. 
        
        Similarly, wind capacity in countries like **Denmark** is severely underreported. 
        Meanwhile, hydro-dominant countries like **Paraguay** and **Norway** correctly top the list, 
        and Gulf states sit near 0%.
        """
    )

    st.divider()

    # ---------------------------------------------------------
    # Chart 3: Country to Fuel Hierarchy (Treemap)
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

    st.plotly_chart(fig_treemap, use_container_width=True)