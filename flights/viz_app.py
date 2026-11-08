"""Interactive dashboard for exploring flight prices in Postgres.

Run:
  streamlit run flights/viz_app.py
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from flights.db import connect, init_db


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _require_env() -> None:
    if not os.getenv("DATABASE_URL"):
        st.error("Missing DATABASE_URL. Set it in `.env` or in environment variables.")
        st.stop()


@st.cache_data(ttl=60)
def _runs(limit: int = 200) -> pd.DataFrame:
    with connect() as con:
        rows = con.execute(
            """
            SELECT id, started_at, status, provider, records_count
            FROM ingest_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            [limit],
        ).fetchall()
    return pd.DataFrame(rows, columns=["ingest_run_id", "started_at", "status", "provider", "records_count"])


@st.cache_data(ttl=60)
def _offers(
    run_ids: list[int] | None,
    direction: str | None,
    dep_start: date | None,
    dep_end: date | None,
) -> pd.DataFrame:
    where = []
    params: list[object] = []
    if run_ids:
        where.append("run_id = ANY(%s)")
        params.append(run_ids)
    if direction and direction != "ALL":
        where.append("direction = %s")
        params.append(direction)
    if dep_start:
        where.append("departure_date >= %s")
        params.append(dep_start)
    if dep_end:
        where.append("departure_date <= %s")
        params.append(dep_end)

    sql = """
        SELECT run_id, fetched_at, direction, departure_date,
               carrier_code, flight_number, price_total_usd
        FROM offers
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY fetched_at, direction, departure_date, price_total_usd"

    with connect() as con:
        rows = con.execute(sql, params).fetchall()
    df = pd.DataFrame(
        rows,
        columns=[
            "run_id",
            "fetched_at",
            "direction",
            "departure_date",
            "carrier_code",
            "flight_number",
            "price_total_usd",
        ],
    )
    if not df.empty:
        df["flight_key"] = df["carrier_code"].astype(str) + " " + df["flight_number"].astype(str)
    return df


def _daily_min(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    g = (
        df.groupby(["direction", "departure_date"], as_index=False)
        .agg(min_price=("price_total_usd", "min"))
        .sort_values(["direction", "departure_date"])
    )
    return g


def main() -> None:
    st.set_page_config(page_title="Flight tracker dashboard", layout="wide")
    st.title("my-flight-tracker — price dashboard")

    _require_env()
    init_db()

    runs = _runs()
    ok_runs = runs[runs["status"] == "ok"]
    st.sidebar.header("Filters")

    direction = st.sidebar.selectbox("Direction", ["ALL", "TLV_VIE", "VIE_TLV"])

    # choose runs
    default_n = 12
    run_ids = st.sidebar.multiselect(
        "Ingest run IDs (latest first)",
        options=ok_runs["ingest_run_id"].tolist(),
        default=ok_runs["ingest_run_id"].head(default_n).tolist(),
    )

    dep_start = st.sidebar.date_input("Departure start (optional)", value=None)
    dep_end = st.sidebar.date_input("Departure end (optional)", value=None)

    threshold = st.sidebar.number_input("Low-price marker ($)", min_value=0.0, value=250.0, step=10.0)

    st.subheader("Recent ingest runs")
    st.dataframe(runs.head(30), width="stretch")

    df = _offers(run_ids or None, direction, dep_start, dep_end)
    if df.empty:
        st.info("No offers match these filters yet.")
        return

    # Flight selection
    flights = sorted(df["flight_key"].dropna().unique().tolist())
    selected_flights = st.sidebar.multiselect("Specific flights (optional)", options=flights, default=[])
    if selected_flights:
        df = df[df["flight_key"].isin(selected_flights)]
        if df.empty:
            st.info("No offers match the selected flights.")
            return

    # --- Chart 1: Price by departure date (multi-run overlay)
    st.subheader("1) Price by departure date (overlay by ingest run)")
    fig1 = px.line(
        df,
        x="departure_date",
        y="price_total_usd",
        color="run_id",
        facet_col="direction" if direction == "ALL" else None,
        markers=True,
        hover_data=["flight_key", "fetched_at"],
        title="Prices per departure date (each line = one ingest run)",
    )
    fig1.update_layout(legend_title_text="run_id", height=420)
    st.plotly_chart(fig1, width="stretch")

    # --- Chart 2: Price timeline over ingestion time (pick a departure date)
    st.subheader("2) Price over time (pick a departure date)")
    dep_dates = sorted(df["departure_date"].dropna().unique().tolist())
    chosen_date = st.selectbox("Departure date", dep_dates)
    df2 = df[df["departure_date"] == chosen_date].copy()
    df2.sort_values("fetched_at", inplace=True)
    fig2 = px.line(
        df2,
        x="fetched_at",
        y="price_total_usd",
        color="flight_key",
        facet_col="direction" if direction == "ALL" else None,
        markers=True,
        title=f"Prices over ingestion time for departure {chosen_date}",
    )
    fig2.update_layout(height=420)
    st.plotly_chart(fig2, width="stretch")

    # --- Chart 3: Daily minimum markers
    st.subheader("3) Lowest daily price markers (min across selected runs)")
    mins = _daily_min(df)
    fig3 = px.scatter(
        mins,
        x="departure_date",
        y="min_price",
        color="direction",
        title="Daily minimum price (across selected runs / flights)",
    )
    fig3.add_hline(y=threshold, line_dash="dash", line_color="red")
    fig3.update_layout(height=420, yaxis_title="min price (USD, 2 pax)")
    st.plotly_chart(fig3, width="stretch")

    # --- Extra: Heatmap (departure date vs observed run_id)
    st.subheader("4) Heatmap: min price by run_id × departure_date")
    pivot = (
        df.groupby(["run_id", "departure_date"], as_index=False)
        .agg(min_price=("price_total_usd", "min"))
        .pivot(index="run_id", columns="departure_date", values="min_price")
    )
    fig4 = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=[str(c) for c in pivot.columns.tolist()],
            y=[str(i) for i in pivot.index.tolist()],
            colorbar=dict(title="min $"),
        )
    )
    fig4.update_layout(height=420, xaxis_title="departure_date", yaxis_title="run_id")
    st.plotly_chart(fig4, width="stretch")

    st.subheader("Raw offers (filtered)")
    st.dataframe(df, width="stretch")


if __name__ == "__main__":
    main()

