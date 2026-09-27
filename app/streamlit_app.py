"""India Logistics Hub Optimizer - Streamlit dashboard.

Sections:
- Demand Forecasting: per-state / India-wide SARIMA forecast, plus
  Top Growth States (fastest-growing states by forecasted volume/amount)
- Growth Gap Analysis: e-way bill growth vs GSDP growth, per-state trend
  and a state-by-state comparison bar chart
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ---------------------------------------------------------------------------
# File locations
# ---------------------------------------------------------------------------

# This file lives at app/streamlit_app.py, so the project root is one level up.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "models"

HISTORY_FILES = {
    "Volume": DATA_DIR / "volume_data.csv",
    "Amount": DATA_DIR / "amount_data.csv",
}
FORECAST_FILES = {
    "Volume": DATA_DIR / "volume_preds.csv",
    "Amount": DATA_DIR / "amount_preds.csv",
}
GROWTH_FILE = DATA_DIR / "growth_summary.csv"

# Growth Gap Analysis uses its own set of files/states — a separate dataset
# from the demand-forecasting one above (different states included/excluded).
GROWTH_BILL_FILE = DATA_DIR / "growth_bill.csv"
GROWTH_GSDP_FILE = DATA_DIR / "growth_gsdp.csv"
GROWTH_COMPARISON_FILE = DATA_DIR / "growth_comparison.csv"

# A few state names need a friendlier label than a plain title-case would give.
STATE_NAME_OVERRIDES = {
    "dnh and dd": "Dadra & Nagar Haveli and Daman & Diu",
}


# ---------------------------------------------------------------------------
# Small helper functions
# ---------------------------------------------------------------------------

def format_state_name(unique_id):
    """Turn a raw unique_id like 'west bengal' into a display-friendly name."""
    if unique_id in STATE_NAME_OVERRIDES:
        return STATE_NAME_OVERRIDES[unique_id]
    return unique_id.title()


def format_value(value, metric):
    """Format a number the way each metric should be read: count vs currency."""
    if metric == "Volume":
        return f"{value:,.0f}"
    return f"₹{value:,.1f} Cr"


@st.cache_data
def load_csv(path, has_date_column=True):
    """Read one CSV. Cached so it only happens once per file, not every time
    the user changes a filter. The history/forecast files have a 'ds' date
    column to parse; growth-related files do not, so they can skip that."""
    if has_date_column:
        return pd.read_csv(path, parse_dates=["ds"])
    return pd.read_csv(path)


def load_history(metric):
    """Load the actual (historical) data for the chosen metric."""
    return load_csv(HISTORY_FILES[metric])


def load_forecast(metric):
    """Load the forecasted data for the chosen metric."""
    return load_csv(FORECAST_FILES[metric])


def build_location_options(history_df):
    """Build the sidebar's location list: 'India' plus every state, sorted
    by the friendly display name. Returns a dict of {display_name: uid}."""
    state_ids = sorted(history_df["unique_id"].unique())
    options = {"India": "ALL"}
    for uid in sorted(state_ids, key=format_state_name):
        options[format_state_name(uid)] = uid
    return options


def scope_actual(history_df, location_uid):
    """Return the actual data for one state, or summed across India."""
    if location_uid == "ALL":
        scoped = history_df.groupby("ds", as_index=False)["y"].sum()
    else:
        scoped = history_df.loc[history_df["unique_id"] == location_uid, ["ds", "y"]]
    return scoped.sort_values("ds").reset_index(drop=True)


def scope_forecast(forecast_df, location_uid):
    """Return the forecast data for one state, or summed across India."""
    if location_uid == "ALL":
        scoped = forecast_df.groupby("ds", as_index=False)["SARIMA"].sum()
    else:
        scoped = forecast_df.loc[
            forecast_df["unique_id"] == location_uid, ["ds", "SARIMA"]
        ]
    return scoped.sort_values("ds").reset_index(drop=True)


def filter_history_range(actual_df, history_range):
    """Trim the actual data to the chosen number of years, for the chart only."""
    if history_range == "All":
        return actual_df
    years = 5 if history_range == "Last 5 years" else 3
    cutoff = actual_df["ds"].max() - pd.DateOffset(years=years)
    return actual_df.loc[actual_df["ds"] >= cutoff]


# ---------------------------------------------------------------------------
# Demand Forecasting — Forecast sub-tab
# ---------------------------------------------------------------------------

def render_forecast_tab():
    """Sidebar controls, headline numbers, chart, and forecast table.
    Lives inside the 'Forecast' sub-tab of Demand Forecasting."""

    # --- Load data, with a friendly error instead of a crash if it's missing ---
    try:
        metric = st.session_state.get("metric", "Volume")
        history_df = load_history(metric)
        forecast_df = load_forecast(metric)
    except FileNotFoundError as error:
        st.error(
            "Could not find the demand data files. Make sure "
            f"volume_data.csv / amount_data.csv and volume_preds.csv / "
            f"amount_preds.csv are inside the 'models' folder.\n\n{error}"
        )
        return

    location_options = build_location_options(history_df)

    # --- Sidebar controls ---
    with st.sidebar:
        st.subheader("Forecast controls")
        metric = st.selectbox("Metric", ["Volume", "Amount"], key="metric")
        location_name = st.selectbox("Location", list(location_options.keys()))
        horizon = st.selectbox("Forecast horizon (months)", [12, 24])
        history_range = st.selectbox(
            "History shown", ["All", "Last 5 years", "Last 3 years"]
        )

    # Reload in case the metric changed after the widgets above ran.
    history_df = load_history(metric)
    forecast_df = load_forecast(metric)
    location_uid = location_options[location_name]

    actual = scope_actual(history_df, location_uid)
    forecast = scope_forecast(forecast_df, location_uid)
    forecast_display = forecast.head(horizon)

    metric_label = "E-Way Bill Volume" if metric == "Volume" else "Assessed Value"

    # --- Headline cards ---
    # These always compare the last 12 actual months to the next 12 forecast
    # months, no matter what horizon is picked for the chart below.
    last_12_actual = actual.tail(12)["y"].sum()
    next_12_forecast = forecast.head(12)["SARIMA"].sum()
    growth_pct = ((next_12_forecast / last_12_actual) - 1) * 100

    col1, col2, col3 = st.columns(3)
    col1.metric(f"Last 12 months ({metric_label.lower()})", format_value(last_12_actual, metric))
    col2.metric("Next 12 months (forecast)", format_value(next_12_forecast, metric))
    col3.metric("Growth vs. last 12 months", f"{growth_pct:+.1f}%")

    # --- Main chart ---
    chart_actual = filter_history_range(actual, history_range)

    # Connect the two lines by starting the forecast line at the last actual point.
    last_point = actual.tail(1).rename(columns={"y": "SARIMA"})[["ds", "SARIMA"]]
    forecast_connected = pd.concat([last_point, forecast_display], ignore_index=True)
    forecast_start_date = last_point["ds"].iloc[0]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=chart_actual["ds"], y=chart_actual["y"],
        name="Historical", mode="lines",
        line=dict(color="#4cc9f0", width=3),
    ))
    fig.add_trace(go.Scatter(
        x=forecast_connected["ds"], y=forecast_connected["SARIMA"],
        name="Forecast", mode="lines",
        line=dict(color="#f72585", width=3, dash="dash"),
        fill="tozeroy", fillcolor="rgba(247, 37, 133, 0.15)",
    ))
    fig.add_vline(
        x=forecast_start_date, line_dash="dot", line_color="#94a3b8",
        annotation_text="Forecast starts", annotation_position="top left",
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        title=dict(text=f"{metric} forecast — {location_name}", x=0.5, xanchor="center", y=0.97, yanchor="top"),
        xaxis_title="Month",
        yaxis_title=metric_label,
        hovermode="x unified",
        height=430,
        legend=dict(orientation="h", yanchor="bottom", y=1.15, x=0, xanchor="left", itemwidth=50),
        margin=dict(l=60, r=60, t=95, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Forecast table + download ---
    st.subheader("Forecast data")
    table = forecast_display.rename(columns={"ds": "Month", "SARIMA": metric_label})
    table["Month"] = table["Month"].dt.strftime("%b %Y")
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.download_button(
        "Download CSV",
        data=table.to_csv(index=False),
        file_name=f"{metric.lower()}_forecast_{location_name}.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# Demand Forecasting — Top Growth States sub-tab
# ---------------------------------------------------------------------------

def render_top_growth_tab():
    """Which states are forecast to grow fastest. Lives inside the
    'Top Growth States' sub-tab of Demand Forecasting."""

    if not GROWTH_FILE.exists():
        st.info("Growth summary data not available yet.")
        return

    growth_df = load_csv(GROWTH_FILE, has_date_column=False)
    growth_df["state"] = growth_df["unique_id"].apply(format_state_name)

    top_volume = growth_df.sort_values("volume_growth", ascending=False).head(10)
    fig = px.bar(
        top_volume, x="volume_growth", y="state", orientation="h",
        title="Top 10 states — Volume growth",
        labels={"volume_growth": "Growth (%)", "state": ""},
        color_discrete_sequence=["#4cc9f0"],
        text="volume_growth",
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(template="plotly_dark", paper_bgcolor="#111827", plot_bgcolor="#111827")
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(range=[0, top_volume["volume_growth"].max() * 1.15])
    st.plotly_chart(fig, use_container_width=True)

    top_amount = growth_df.sort_values("amount_growth", ascending=False).head(10)
    fig = px.bar(
        top_amount, x="amount_growth", y="state", orientation="h",
        title="Top 10 states — Amount growth",
        labels={"amount_growth": "Growth (%)", "state": ""},
        color_discrete_sequence=["#f72585"],
        text="amount_growth",
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(template="plotly_dark", paper_bgcolor="#111827", plot_bgcolor="#111827")
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(range=[0, top_amount["amount_growth"].max() * 1.15])
    st.plotly_chart(fig, use_container_width=True)

    st.caption("Growth = next 12 forecast months vs. last 12 actual months.")


# ---------------------------------------------------------------------------
# Demand Forecasting — top-level section (wraps the two sub-tabs above)
# ---------------------------------------------------------------------------

def render_demand_forecasting_section():
    """Top-level Demand Forecasting section: one heading, two sub-tabs."""
    st.header("Demand Forecasting")
    st.caption(
        "Monthly demand outlook based on GST E-Way Bill data, "
        "and which states are forecast to grow fastest."
    )

    tab_forecast, tab_top_growth = st.tabs(["Forecast", "Top Growth States"])
    with tab_forecast:
        render_forecast_tab()
    with tab_top_growth:
        render_top_growth_tab()


# ---------------------------------------------------------------------------
# Growth Gap Analysis (only shown if the growth-gap files exist)
# ---------------------------------------------------------------------------

def load_growth_data():
    """Load the growth-gap files: yearly bill/GSDP values (for the trend
    chart) and the pre-computed CAGR comparison (for the bar chart)."""
    bill_df = load_csv(GROWTH_BILL_FILE, has_date_column=False)
    gsdp_df = load_csv(GROWTH_GSDP_FILE, has_date_column=False)
    comparison_df = load_csv(GROWTH_COMPARISON_FILE, has_date_column=False)
    return bill_df, gsdp_df, comparison_df


def build_growth_location_options(bill_df):
    """Build the state list for Growth Gap Analysis. This is a separate set
    of states from the demand-forecasting data above (e.g. Ladakh and
    'other territory' are excluded here but may exist in the forecast data)."""
    state_ids = sorted(bill_df["state"].unique(), key=format_state_name)
    return {format_state_name(uid): uid for uid in state_ids}


def render_growth_gap_analysis():
    """Draw the Growth Gap Analysis section: a per-state yearly trend of
    e-way bill growth vs GSDP growth, and a bar chart summarising the CAGR
    gap across all states."""

    st.header("Growth Gap Analysis")
    st.caption(
        "Comparing e-way bill growth to GSDP growth, state by state, "
        "to spot where logistics activity is lagging or outpacing the economy."
    )

    try:
        bill_df, gsdp_df, comparison_df = load_growth_data()
    except FileNotFoundError as error:
        st.error(
            "Could not find the growth comparison data files. Make sure "
            "growth_bill.csv, growth_gsdp.csv, and growth_comparison.csv "
            f"are inside the 'models' folder.\n\n{error}"
        )
        return

    growth_location_options = build_growth_location_options(bill_df)

    # A dedicated sidebar block for this section, separate from the
    # forecasting controls above, using its own set of states.
    with st.sidebar:
        st.subheader("Growth gap controls")
        growth_state_name = st.selectbox(
            "State (for trend chart)",
            list(growth_location_options.keys()),
            key="growth_state",
        )
    growth_state_uid = growth_location_options[growth_state_name]

    tab_trend, tab_bar = st.tabs(["Yearly Trend", "State Comparison"])
    year_cols = ["20-21", "21-22", "22-23"]

    # --- Tab 1: per-state line trend ---
    with tab_trend:
        bill_row = bill_df.loc[bill_df["state"] == growth_state_uid, year_cols].iloc[0]
        gsdp_row = gsdp_df.loc[gsdp_df["state"] == growth_state_uid, year_cols].iloc[0]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=year_cols, y=bill_row.values,
            name="E-Way Bill Growth", mode="lines+markers",
            line=dict(color="#4cc9f0", width=3), marker=dict(size=8),
        ))
        fig.add_trace(go.Scatter(
            x=year_cols, y=gsdp_row.values,
            name="GSDP Growth", mode="lines+markers",
            line=dict(color="#f72585", width=3), marker=dict(size=8),
        ))
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#111827",
            plot_bgcolor="#111827",
            title=dict(
                text=f"Bill vs GSDP Growth — {growth_state_name}",
                x=0.5, xanchor="center", y=0.97, yanchor="top",
            ),
            xaxis_title="Year",
            yaxis_title="Growth (%)",
            hovermode="x unified",
            height=430,
            legend=dict(orientation="h", yanchor="bottom", y=1.15, x=0, xanchor="left"),
            margin=dict(l=60, r=60, t=95, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- Tab 2: state comparison bar chart ---
    with tab_bar:
        plot_df = comparison_df.copy()
        plot_df["state_label"] = plot_df["state"].apply(format_state_name)
        plot_df["color"] = plot_df["diff"].apply(lambda x: "#2ecc71" if x > 0 else "#e74c3c")

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=plot_df["diff"], y=plot_df["state_label"],
            orientation="h", marker_color=plot_df["color"],
        ))
        fig.add_vline(x=0, line_color="#94a3b8", line_width=1)
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#111827",
            plot_bgcolor="#111827",
            title=dict(
                text="Bill Growth vs GSDP Growth Gap by State",
                x=0.5, xanchor="center", y=0.97, yanchor="top",
            ),
            xaxis_title="Growth Gap (Bill CAGR − GSDP CAGR)",
            yaxis_title="",
            height=850,
            margin=dict(l=140, r=60, t=80, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.caption(
            "Negative (red) = e-way bill growth lagging GSDP growth → "
            "potential untapped logistics demand. Positive (green) = "
            "logistics growth already outpacing the economy."
        )


# ---------------------------------------------------------------------------
# App entry point
# ---------------------------------------------------------------------------

st.set_page_config(page_title="India Logistics Hub Optimizer", layout="wide")

SECTIONS = {"Demand Forecasting": render_demand_forecasting_section}

if GROWTH_BILL_FILE.exists() and GROWTH_GSDP_FILE.exists() and GROWTH_COMPARISON_FILE.exists():
    SECTIONS["Growth Gap Analysis"] = render_growth_gap_analysis

with st.sidebar:
    st.title("Navigation")
    active_section = st.radio("Section", list(SECTIONS.keys()))
    st.divider()

SECTIONS[active_section]()