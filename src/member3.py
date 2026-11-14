"""Part 3 — Generation & ML (charts 7-9).

7. Estimated vs actual generation (scatter, log axes)
8. Country clusters by energy mix (K-Means → choropleth)        ⭐ advanced
9. Cluster profiles (parallel coordinates)                       ⭐ advanced
10. Data reality check — dataset vs official figures (coverage bar chart)

Decisions and their reasons: ANALYSIS_NOTES.md ("ML plan", "K-Means result").
"""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from src.member1 import FUEL_COLORS

from src.data_loader import load_clean

# Fuels used as clustering features; every other fuel is merged into "Other"
CLUSTER_FUELS = ["Coal", "Gas", "Oil", "Nuclear", "Hydro", "Wind", "Solar", "Biomass"]


# --------------------------------------------------------------------------------------
# 7. Estimated vs actual generation
# --------------------------------------------------------------------------------------
MIN_COMPARABLE_PLANTS = 10   # countries need at least this many plants with both values to be selectable


@st.cache_data
def comparable_plants() -> pd.DataFrame:
    """Plants with BOTH actual (reported) and estimated 2017 generation > 0 (log axes need > 0).

    Actual generation exists for only ~27% of plants (mostly US), so this chart has its own country
    selector instead of the sidebar filter — otherwise most country selections would be empty.
    """
    df = load_clean()
    d = df.dropna(subset=["generation_gwh_2017", "estimated_generation_gwh_2017"])
    return d[(d["generation_gwh_2017"] > 0) & (d["estimated_generation_gwh_2017"] > 0)]


def chart_7(df):
    st.subheader("7. How accurate is the dataset's generation estimate?")
    all_d = comparable_plants()
    counts = all_d["country_long"].value_counts()
    options = ["All countries"] + [f"{c} ({n:,})" for c, n in counts[counts >= MIN_COMPARABLE_PLANTS].items()]
    choice = st.selectbox("Country (only countries with reported generation data)", options, key="c7_country")
    d = all_d if choice == "All countries" else all_d[all_d["country_long"] == choice.rsplit(" (", 1)[0]]

    fig = px.scatter(
        d, x="estimated_generation_gwh_2017", y="generation_gwh_2017", color="primary_fuel",        color_discrete_map=FUEL_COLORS,
        log_x=True, log_y=True, opacity=0.5, render_mode="webgl", hover_name="name",
        hover_data={"country_long": True, "capacity_mw": ":.0f"},
        labels={"estimated_generation_gwh_2017": "Estimated generation 2017 (GWh, WRI model)",
                "generation_gwh_2017": "Actual generation 2017 (GWh, reported)",
                "primary_fuel": "Primary fuel"},
    )
    lo = min(d["estimated_generation_gwh_2017"].min(), d["generation_gwh_2017"].min())
    hi = max(d["estimated_generation_gwh_2017"].max(), d["generation_gwh_2017"].max())
    fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", name="Perfect estimate (y = x)",
                             line=dict(color="gray", dash="dash")))
    fig.update_layout(height=520)
    st.plotly_chart(fig, width="stretch")

    # Per-fuel bias: median of actual / estimated (>1 → model underestimates)
    ratio = (d["generation_gwh_2017"] / d["estimated_generation_gwh_2017"]).groupby(d["primary_fuel"]).median()
    st.caption(
        f"{len(d):,} plants have both values ({d['is_us'].mean():.0%} in the US). "
        f"Only {len(counts)} countries report actual generation, so this chart uses its own country selector "
        "(sidebar filters do not apply). "
        "Points above the dashed line: the plant produced more than the estimate. "
        "Median actual/estimated ratio by fuel: "
        + ", ".join(f"{f} {r:.2f}" for f, r in ratio.sort_values().items())
    )


# --------------------------------------------------------------------------------------
# K-Means (computed on ALL countries — sidebar filters do not apply, see chart_8 caption)
# --------------------------------------------------------------------------------------
@st.cache_data
def country_mix(min_capacity_mw: float) -> pd.DataFrame:
    """Rows = countries above the capacity threshold, columns = capacity shares per fuel."""
    df = load_clean()
    cap = df.pivot_table(index=["country", "country_long"], columns="primary_fuel",
                         values="capacity_mw", aggfunc="sum", fill_value=0)
    totals = cap.sum(axis=1)
    shares = cap[totals > min_capacity_mw].div(totals[totals > min_capacity_mw], axis=0)
    X = shares.reindex(columns=CLUSTER_FUELS, fill_value=0)
    X["Other"] = (1 - X.sum(axis=1)).clip(lower=0)
    X["total_gw"] = totals[totals > min_capacity_mw] / 1000
    return X.reset_index()


def _name_clusters(centroids: pd.DataFrame) -> dict:
    """Readable cluster names from centroids: '<Fuel>-dominant' if one fuel ≥ 50%, else 'Mixed'."""
    names = {}
    for cid, row in centroids.iterrows():
        top = row.idxmax()
        names[cid] = f"{top}-dominant" if row[top] >= 0.5 else f"Mixed (most: {top})"
    # make names unique if two clusters get the same label (#1, #2 …)
    base = dict(names)
    counter = {}
    for cid, n in base.items():
        if list(base.values()).count(n) > 1:
            counter[n] = counter.get(n, 0) + 1
            names[cid] = f"{n} #{counter[n]}"
    return names


@st.cache_data
def run_kmeans(k: int, min_capacity_mw: float):
    mix = country_mix(min_capacity_mw)
    feats = CLUSTER_FUELS + ["Other"]
    # n_init=50: many random restarts → result does not depend on row order / initialisation
    km = KMeans(n_clusters=k, n_init=50, random_state=42).fit(mix[feats])
    mix = mix.copy()
    mix["cluster_id"] = km.labels_
    centroids = pd.DataFrame(km.cluster_centers_, columns=feats)
    names = _name_clusters(centroids)
    mix["cluster"] = mix["cluster_id"].map(names)
    sil = silhouette_score(mix[feats], km.labels_)
    return mix, centroids.rename(index=names), sil


def _cluster_controls():
    c1, c2 = st.columns(2)
    k = c1.slider("Number of clusters (k)", 2, 8, 4, key="k_clusters",
                  help="k = 4 chosen by elbow method; silhouette is almost equal for k = 3 and 4.")
    thr = c2.select_slider("Min. national capacity (MW)", options=[1000, 2000, 5000, 10000, 20000],
                           value=5000, key="k_threshold",
                           help="Small countries with 1-2 plants distort shares, so they are excluded.")
    return k, thr


# --------------------------------------------------------------------------------------
# 8. Cluster map
# --------------------------------------------------------------------------------------
SELECTED_COLOR = "#FFC400"   # amber/gold — not used by any cluster (Plotly qualitative palette)
NO_COUNTRY = "— none (show all clusters) —"


def _cluster_colors(order):
    """Same color per cluster in the map (chart 8) and the parallel coordinates (chart 9)."""
    return {n: px.colors.qualitative.Plotly[i % 10] for i, n in enumerate(order)}


def _clicked_country(event):
    """ISO-3 code of the country clicked on the map (Streamlit selection event), or None."""
    try:
        points = event.selection.points if hasattr(event, "selection") else event["selection"]["points"]
    except (KeyError, TypeError, AttributeError):
        return None
    for p in points or []:
        loc = p.get("location") if isinstance(p, dict) else None
        if loc:
            return loc
    return None


def chart_8(df):
    """Title → controls → map. Returns (k, thr, selected country code or None) for chart 9."""
    st.subheader("8. Countries grouped by energy mix (K-Means)")
    k, thr = _cluster_controls()
    mix, centroids, sil = run_kmeans(k, thr)
    order = sorted(mix["cluster"].unique())
    names = dict(zip(mix["country"], mix["country_long"]))

    # One selection drives both charts: choose a country (dropdown or click on the map) →
    # its cluster is highlighted, the country itself is drawn in a separate color in chart 8 and chart 9.
    # (Legend clicks and parcoords brushing stay inside the browser; Streamlit cannot read them.)
    sel_key = f"country_sel_{thr}"
    if "pending_country" in st.session_state:          # set by a map click in the previous run
        st.session_state[sel_key] = st.session_state.pop("pending_country")
    options = [NO_COUNTRY] + sorted(mix["country"], key=lambda c: names[c])
    selected = st.selectbox("Select a country (or click one on the map)", options, key=sel_key,
                            format_func=lambda c: c if c == NO_COUNTRY else names[c])
    selected = None if selected == NO_COUNTRY else selected
    st.caption("These settings also apply to chart 9.")

    colors = _cluster_colors(order)
    if selected is None:
        mix = mix.assign(shown=mix["cluster"])
    else:
        sel_cluster = mix.loc[mix["country"] == selected, "cluster"].iloc[0]
        mix = mix.assign(shown=np.select(
            [mix["country"] == selected, mix["cluster"] == sel_cluster],
            [f"Selected: {names[selected]}", mix["cluster"]], default="Other clusters"))
        colors["Other clusters"] = "lightgray"
        colors[f"Selected: {names[selected]}"] = SELECTED_COLOR

    fig = px.choropleth(
        mix, locations="country", locationmode="ISO-3", color="shown",
        hover_name="country_long",
        hover_data={"country": False, "shown": False, "cluster": True, "total_gw": ":.1f",
                    **{f: ":.0%" for f in CLUSTER_FUELS}},
        category_orders={"shown": order + ["Other clusters"]},
        color_discrete_map=colors,
        projection="natural earth",
        labels={"cluster": "Cluster", "shown": "Cluster", "total_gw": "Total capacity (GW)"},
    )
    fig.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0), clickmode="event+select")
    event = st.plotly_chart(fig, width="stretch", on_select="rerun", selection_mode="points",
                            key=f"cluster_map_{k}_{thr}_{selected}")

    # Map click → select that country (applied before the dropdown is drawn in the next run)
    clicked = _clicked_country(event)
    if clicked and clicked != selected and clicked in names:
        st.session_state["pending_country"] = clicked
        st.rerun()

    st.caption(
        f"{len(mix)} countries with > {thr:,} MW capacity · k = {k} · silhouette = {sil:.2f}. "
        "Computed on all countries (sidebar filters do not apply). "
        "⚠️ Clusters reflect the dataset's coverage: e.g. Denmark falls in a coal cluster because most of its "
        "wind capacity (> 6 GW in reality) is missing from the data."
    )
    with st.expander("Cluster profiles (average capacity share per fuel)"):
        st.dataframe(centroids.style.format("{:.0%}"), width="stretch")
    return k, thr, selected


# --------------------------------------------------------------------------------------
# 9. Parallel coordinates
# --------------------------------------------------------------------------------------
def chart_9(df, k, thr, selected=None):
    st.subheader("9. What separates the clusters? (parallel coordinates)")
    mix, _, _ = run_kmeans(k, thr)
    feats = CLUSTER_FUELS + ["Other"]

    # parallel_coordinates needs a numeric color → cluster ids sorted by name (0..n-1),
    # selected country gets id n (extra color). Stepped colorscale = one flat color per id.
    order = sorted(mix["cluster"].unique())
    n = len(order)
    mix = mix.assign(cid=mix["cluster"].map({c: i for i, c in enumerate(order)}))
    if selected is not None:
        sel_cluster = mix.loc[mix["country"] == selected, "cluster"].iloc[0]
        mix = mix[mix["cluster"] == sel_cluster].copy()
        mix.loc[mix["country"] == selected, "cid"] = n
        mix = mix.sort_values("cid")            # selected country drawn last → on top

    palette = px.colors.qualitative.Plotly
    ids = list(range(n)) + [n]
    cols = [palette[i % len(palette)] for i in range(n)] + [SELECTED_COLOR]
    colorscale = []
    for i, c in zip(ids, cols):
        colorscale += [[i / (n + 1), c], [(i + 1) / (n + 1), c]]

    fig = px.parallel_coordinates(
        mix, color="cid", dimensions=feats, color_continuous_scale=colorscale,
        range_color=[-0.5, n + 0.5], labels={f: f"{f} share" for f in feats},
    )
    fig.update_traces(dimensions=[dict(range=[0, 1], label=f, values=mix[f]) for f in feats])
    ticktext = order + ["Selected country"]
    # wider left/top margins: the first axis label ("Coal") was clipped at the chart edge
    fig.update_layout(height=480, margin=dict(l=70, r=40, t=70, b=40), coloraxis_colorbar=dict(
        title="Cluster", tickvals=ids if selected is not None else ids[:-1],
        ticktext=ticktext if selected is not None else order))
    st.plotly_chart(fig, width="stretch")
    st.caption("Each line is one country; the height where it crosses an axis is that fuel's share of the "
               "country's capacity. Drag along an axis to filter (brush), e.g. Hydro > 50%. "
               "Select a country above to isolate its cluster.")
    if selected is not None:
        sel_name = mix.loc[mix["country"] == selected, "country_long"].iloc[0]
        members = [f"**{c}**" if c == sel_name else c for c in sorted(mix["country_long"])]
        st.markdown(f"**{sel_cluster}** ({len(mix)} countries): " + ", ".join(members))


# --------------------------------------------------------------------------------------
# 10. Data reality check — dataset vs official figures
# --------------------------------------------------------------------------------------
# Official end-2019 wind / solar capacity (like-for-like: same technology, same unit; totals are not
# compared because "total capacity" is defined differently per country). Sources in the hover + caption.
OFFICIAL = [
    # country code, country, fuel, official MW, source
    ("USA", "United States", "Wind", 103_000, "EIA, Today in Energy (end-2019)"),
    ("GBR", "United Kingdom", "Wind", 24_000, "BEIS via Utility Week (onshore 14.2 + offshore 9.8 GW, end-2019)"),
    ("DEU", "Germany", "Wind", 60_700, "Fraunhofer ISE (onshore 53.1 + offshore 7.6 GW, Oct-2019)"),
    ("DEU", "Germany", "Solar", 48_600, "Fraunhofer ISE (Oct-2019)"),
    ("DNK", "Denmark", "Wind", 6_000, "Wind Denmark via NS Energy (> 6 GW, 2019; lower bound)"),
    ("TUR", "Turkey", "Wind", 8_056, "TÜREB wind statistics report 2019"),
    ("TUR", "Turkey", "Solar", 5_995, "TEİAŞ via TaiyangNews (end-2019)"),
]
OFFICIAL_RENEWABLE_SHARE = {"Turkey": (0.452, "EMRA Electricity Market Report 2019")}
COVERAGE_COLORS = {"Good (≥ 90%)": "#1D9E75", "Partial (25-90%)": "#EF9F27", "Poor (< 25%)": "#E24B4A"}


@st.cache_data
def reality_check_table() -> pd.DataFrame:
    full = load_clean()
    rows = []
    for code, country, fuel, official_mw, source in OFFICIAL:
        dataset_mw = full.loc[(full["country"] == code) & (full["primary_fuel"] == fuel), "capacity_mw"].sum()
        cov = dataset_mw / official_mw
        rows.append({"Country": country, "Fuel": fuel, "Item": f"{country} · {fuel}",
                     "Dataset (GW)": dataset_mw / 1000, "Official (GW)": official_mw / 1000,
                     "Coverage": cov, "Source": source,
                     "Quality": "Good (≥ 90%)" if cov >= 0.9 else "Partial (25-90%)" if cov >= 0.25 else "Poor (< 25%)"})
    return pd.DataFrame(rows).sort_values("Coverage", ascending=False)


def chart_10(df):
    st.subheader("10. Reality check: how much of the real system is in the dataset?")
    rc = reality_check_table()   # independent of sidebar filters

    c1, c2 = st.columns([2, 1])
    view = c1.radio("View", ["Coverage (%)", "Dataset vs official (GW)"], horizontal=True, key="rc_view")
    fuels = c2.multiselect("Technology", ["Wind", "Solar"], default=["Wind", "Solar"], key="rc_fuels")
    d = rc[rc["Fuel"].isin(fuels)]
    if d.empty:
        st.info("Select at least one technology.")
        return

    hover = {"Dataset (GW)": ":.1f", "Official (GW)": ":.1f", "Coverage": ":.0%", "Source": True}
    if view == "Coverage (%)":
        fig = px.bar(d, x="Coverage", y="Item", orientation="h", color="Quality",
                     color_discrete_map=COVERAGE_COLORS, text=d["Coverage"].map("{:.0%}".format),
                     hover_data={**hover, "Quality": False, "Item": False},
                     category_orders={"Item": list(d["Item"]), "Quality": list(COVERAGE_COLORS)},
                     labels={"Coverage": "Share of official capacity found in the dataset", "Item": ""})
        fig.add_vline(x=1, line_dash="dash", line_color="gray", annotation_text="100% = complete",
                      annotation_position="bottom right")
        fig.update_layout(xaxis_tickformat=".0%", xaxis_range=[0, 1.15])
    else:
        long = d.melt(id_vars=["Item", "Source", "Coverage"], value_vars=["Dataset (GW)", "Official (GW)"],
                      var_name="Figure", value_name="GW")
        fig = px.bar(long, x="GW", y="Item", color="Figure", barmode="group", orientation="h",
                     color_discrete_map={"Dataset (GW)": "#7F77DD", "Official (GW)": "#B4B2A9"},
                     hover_data={"Source": True, "Coverage": ":.0%", "Item": False},
                     category_orders={"Item": list(d["Item"])},
                     labels={"GW": "Installed capacity (GW)", "Item": ""})
    fig.update_layout(height=380, legend_title_text="")
    st.plotly_chart(fig, width="stretch")

    tr = load_clean().query("country == 'TUR'")
    share_ds = tr.loc[tr["is_renewable"], "capacity_mw"].sum() / tr["capacity_mw"].sum()
    share_off, src = OFFICIAL_RENEWABLE_SHARE["Turkey"]
    m1, m2 = st.columns(2)
    m1.metric("Turkey renewable share — dataset", f"{share_ds:.0%}")
    m2.metric("Turkey renewable share — official (2019)", f"{share_off:.0%}",
              delta=f"{(share_off - share_ds) * 100:+.0f} pp missing", delta_color="off")
    st.caption(
        "Like-for-like spot check (same technology, end-2019 official figures; dataset capacity years vary "
        "2017-2019, so the comparison is approximate). Large utility-scale fleets (US, UK wind) are almost "
        "fully covered; countries with many small wind/solar installations (Germany, Turkey, Denmark) are "
        "largely missing → renewable shares are underestimated there, which explains e.g. Denmark landing in "
        f"a coal cluster (chart 8). Sources: {'; '.join([r[4] for r in OFFICIAL] + [src])}."
    )


def render(df):
    chart_7(df)
    st.divider()
    k, thr, selected = chart_8(df)
    chart_9(df, k, thr, selected)
    st.divider()
    chart_10(df)