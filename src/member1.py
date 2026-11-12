"""Part 1 — Geography (charts 1-3).

1. Plant map (scatter map)                        ⭐ advanced
2. Renewable share by country (choropleth)        ⭐ advanced
3. Country → fuel hierarchy (treemap)             ⭐ advanced

Plan and insights: ANALYSIS_NOTES.md ("Chart plan").
Each function receives the FILTERED dataframe and draws one chart with st.plotly_chart.
"""
import plotly.express as px
import streamlit as st


def chart_1(df):
    st.subheader("1. TODO — Global map of power plants")
    st.info("Placeholder.")


def chart_2(df):
    st.subheader("2. TODO — Renewable share by country")
    st.info("Placeholder.")


def chart_3(df):
    st.subheader("3. TODO — Country → fuel treemap")
    st.info("Placeholder.")


def render(df):
    chart_1(df)
    chart_2(df)
    chart_3(df)