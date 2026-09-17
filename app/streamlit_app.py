"""Demand forecasting section for the logistics hub optimizer."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA


# Use the available page width: the chart is the focus of this section.
st.set_page_config(layout="wide")


# The data directory is relative to the project root, not Streamlit's launch folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILES = {
    "Volume": PROJECT_ROOT / "models" / "volume_data_sorted.csv",
    "Amount": PROJECT_ROOT / "models" / "amount_data_sorted.csv",
}

STATES = [
    "andaman and nicobar", "andhra pradesh", "arunachal pradesh", "assam",
    "bihar", "chandigarh", "chhattisgarh", "dadra and nagar haveli",
    "daman and diu", "delhi", "goa", "gujarat", "haryana",
    "himachal pradesh", "jammu and kashmir", "jharkhand", "karnataka",
    "kerala", "ladakh", "lakshadweep", "madhya pradesh", "maharashtra",
    "manipur", "meghalaya", "mizoram", "nagaland", "odisha",
    "other territory", "puducherry", "punjab", "rajasthan", "sikkim",
    "tamil nadu", "telangana", "tripura", "uttar pradesh", "uttarakhand",
    "west bengal",
]


@st.cache_data
def load_historical_data(metric):
    """Read a metric's monthly state-level history once and cache the result."""
    return pd.read_csv(DATA_FILES[metric], parse_dates=["ds"])


@st.cache_resource
def fit_forecasting_model(metric):
    """Fit one SARIMA model per state and cache it separately for each metric."""
    data = load_historical_data(metric)
    sarima = AutoARIMA(season_length=12, alias="SARIMA")
    model = StatsForecast(models=[sarima], freq="MS")
    model.fit(data)
    return model


def select_scope_data(actual_data, forecast_data, scope):
    """Return either India totals or one selected state's actuals and forecast."""
    if scope == "India":
        actual = actual_data.groupby("ds", as_index=False)["y"].sum()
        forecast = forecast_data.groupby("ds", as_index=False)["SARIMA"].sum()
    else:
        actual = actual_data.loc[actual_data["unique_id"] == scope, ["ds", "y"]]
        forecast = forecast_data.loc[
            forecast_data["unique_id"] == scope, ["ds", "SARIMA"]
        ]

    return actual.sort_values("ds"), forecast.sort_values("ds")


# This is a section within the wider single-page application. The inputs live in
# the sidebar, keeping the main canvas free for the forecast result.
with st.sidebar:
    st.subheader("Forecast controls")
    st.caption("Choose the demand measure and location to analyse.")
    metric = st.selectbox("Metric", ["Volume", "Amount"])
    scope = st.selectbox("Location", ["India", *STATES])
    run_forecast = st.button("Generate forecast", type="primary", use_container_width=True)

st.header("Demand Forecasting")
st.caption("Monthly demand outlook for India logistics planning · 12-month horizon")

if run_forecast:
    # Data and fitted models are cached, so changing only the scope is quick.
    historical_data = load_historical_data(metric)
    forecasting_model = fit_forecasting_model(metric)
    forecast_data = forecasting_model.predict(h=12)

    actual, forecast = select_scope_data(historical_data, forecast_data, scope)

    # Add the final observed value to the forecast line so both lines meet cleanly.
    last_actual = actual.tail(1).rename(columns={"y": "SARIMA"})
    forecast_with_connection = pd.concat(
        [last_actual[["ds", "SARIMA"]], forecast], ignore_index=True
    )

    metric_label = "Bill Volume" if metric == "Volume" else "Bill Amount"
    boundary_date = last_actual["ds"].iloc[0]
    last_actual_value = last_actual["SARIMA"].iloc[0]
    average_forecast = forecast["SARIMA"].mean()
    forecast_change = ((forecast["SARIMA"].iloc[-1] / last_actual_value) - 1) * 100

    # A few headline numbers make the trend easy to scan before reading the chart.
    latest, average, change = st.columns(3)
    latest.metric(f"Latest {metric_label.lower()}", f"{last_actual_value:,.0f}")
    average.metric("Average next 12 months", f"{average_forecast:,.0f}")
    change.metric("Change by month 12", f"{forecast_change:+.1f}%")

    with st.container(border=True):
        fig, ax = plt.subplots(figsize=(16, 7))
        fig.patch.set_facecolor("#111827")
        ax.set_facecolor("#111827")

        ax.plot(
            actual["ds"], actual["y"], color="#4cc9f0", linewidth=2.8,
            label="Historical demand",
        )
        ax.plot(
            forecast_with_connection["ds"], forecast_with_connection["SARIMA"],
            color="#f72585", linewidth=2.8, linestyle="--", label="Forecast",
        )
        ax.fill_between(
            forecast_with_connection["ds"], forecast_with_connection["SARIMA"], 0,
            color="#f72585", alpha=0.16,
        )
        ax.axvline(boundary_date, color="#94a3b8", linestyle=":", linewidth=1.5)
        ax.annotate(
            "FORECAST STARTS", xy=(boundary_date, 0.97),
            xycoords=("data", "axes fraction"), xytext=(8, 0),
            textcoords="offset points", color="#cbd5e1", fontsize=9, va="top",
        )

        ax.set_title(
            f"{metric} forecast · {scope.title()}", loc="left", pad=18,
            color="#f8fafc", fontsize=18, fontweight="semibold",
        )
        ax.set_xlabel("Date", color="#cbd5e1", labelpad=12)
        ax.set_ylabel(metric_label, color="#cbd5e1", labelpad=12)
        ax.tick_params(colors="#cbd5e1", labelsize=10)
        ax.legend(frameon=False, labelcolor="#e2e8f0", loc="upper left")
        ax.grid(axis="y", color="#334155", alpha=0.5, linewidth=0.8)
        sns.despine(ax=ax, top=True, right=True, left=False, bottom=False)
        for spine in ax.spines.values():
            spine.set_color("#475569")
        fig.tight_layout(pad=2)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
else:
    st.info("Choose a metric and location in the sidebar, then select **Generate forecast**.")
