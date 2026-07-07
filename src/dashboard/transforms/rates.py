"""Rates and spread transforms."""

from __future__ import annotations

import pandas as pd

from dashboard.transforms.returns import WINDOWS


CURVE_PAIRS = {
    "2s10s": ("us_10y_yield", "us_2y_yield"),
    "5s30s": ("us_30y_yield", "us_5y_yield"),
    "10s30s": ("us_30y_yield", "us_10y_yield"),
}
HIBOR_SOFR_PAIRS = {
    "hibor_on_minus_sofr": "hibor_on",
    "hibor_1m_minus_sofr": "hibor_1m",
    "hibor_3m_minus_sofr": "hibor_3m",
    "hibor_6m_minus_sofr": "hibor_6m",
}
US_RATE_SPREAD_PAIRS = {
    "sofr_minus_effr": ("sofr", "effr"),
    "iorb_minus_effr": ("iorb", "effr"),
}
CROSS_MARKET_YIELD_DIFF_PAIRS = {
    "eurusd_3m_yield_diff": ("eur_3m_yield", "us_3m_tbill_yield"),
    "eurusd_2y_yield_diff": ("eur_2y_yield", "us_2y_yield"),
    "eurusd_10y_yield_diff": ("eur_10y_yield", "us_10y_yield"),
    "usdjpy_2y_yield_diff": ("jgb_2y", "us_2y_yield"),
    "usdjpy_10y_yield_diff": ("jgb_10y", "us_10y_yield"),
}


def calculate_bps_changes(df: pd.DataFrame, as_of: str = "latest") -> pd.DataFrame:
    rows = []
    for metric_id, group in _prepared(df).groupby("metric_id"):
        group = group.sort_values("date")
        latest = _latest(group, as_of)
        if latest is None:
            continue
        row = {"metric_id": metric_id, "latest_level": latest.value, "latest_date": latest.date}
        for label, days in WINDOWS.items():
            row[f"{label}_change_bps"] = _bps_change_from(group, latest.date, days)
        ytd_days = (latest.date - pd.Timestamp(year=latest.date.year, month=1, day=1)).days
        row["YTD_change_bps"] = _bps_change_from(group, latest.date, ytd_days)
        rows.append(row)
    return pd.DataFrame(rows)


def calculate_curve_spreads(df: pd.DataFrame, as_of: str = "latest") -> pd.DataFrame:
    data = _prepared(df)
    if data.empty:
        return pd.DataFrame(columns=["date", "spread_id", "value"])
    if as_of != "latest":
        data = data[data["date"] <= pd.to_datetime(as_of)]
    wide = data.pivot_table(index="date", columns="metric_id", values="value", aggfunc="last")
    frames = []
    for spread_id, (long_id, short_id) in CURVE_PAIRS.items():
        if long_id not in wide or short_id not in wide:
            continue
        series = (wide[long_id] - wide[short_id]) * 100
        frames.append(
            pd.DataFrame(
                {"date": series.index, "spread_id": spread_id, "metric_id": f"us_{spread_id}", "value": series.values}
            ).dropna()
        )
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", "spread_id", "value"])


def calculate_hibor_sofr_spreads(df: pd.DataFrame, as_of: str = "latest") -> pd.DataFrame:
    data = _prepared(df)
    if data.empty:
        return pd.DataFrame(columns=["date", "metric_id", "value"])
    if as_of != "latest":
        data = data[data["date"] <= pd.to_datetime(as_of)]
    wide = data.pivot_table(index="date", columns="metric_id", values="value", aggfunc="last")
    if "sofr" not in wide:
        return pd.DataFrame(columns=["date", "metric_id", "value"])
    frames = []
    for spread_id, hibor_id in HIBOR_SOFR_PAIRS.items():
        if hibor_id not in wide:
            continue
        series = (wide[hibor_id] - wide["sofr"]) * 100
        frames.append(pd.DataFrame({"date": series.index, "metric_id": spread_id, "value": series.values}).dropna())
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", "metric_id", "value"])


def calculate_us_rate_spreads(df: pd.DataFrame, as_of: str = "latest") -> pd.DataFrame:
    data = _prepared(df)
    if data.empty:
        return pd.DataFrame(columns=["date", "metric_id", "value"])
    if as_of != "latest":
        data = data[data["date"] <= pd.to_datetime(as_of)]
    wide = data.pivot_table(index="date", columns="metric_id", values="value", aggfunc="last")
    frames = []
    for spread_id, (left_id, right_id) in US_RATE_SPREAD_PAIRS.items():
        if left_id not in wide or right_id not in wide:
            continue
        series = (wide[left_id] - wide[right_id]) * 100
        frames.append(pd.DataFrame({"date": series.index, "metric_id": spread_id, "value": series.values}).dropna())
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", "metric_id", "value"])


def calculate_cross_market_yield_differentials(df: pd.DataFrame, as_of: str = "latest") -> pd.DataFrame:
    data = _prepared(df)
    if data.empty:
        return pd.DataFrame(columns=["date", "metric_id", "value"])
    if as_of != "latest":
        data = data[data["date"] <= pd.to_datetime(as_of)]
    wide = data.pivot_table(index="date", columns="metric_id", values="value", aggfunc="last")
    frames = []
    for metric_id, (local_id, usd_id) in CROSS_MARKET_YIELD_DIFF_PAIRS.items():
        if local_id not in wide or usd_id not in wide:
            continue
        series = (wide[local_id] - wide[usd_id]) * 100
        frames.append(pd.DataFrame({"date": series.index, "metric_id": metric_id, "value": series.values}).dropna())
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", "metric_id", "value"])


def _prepared(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    data = df.copy()
    data["date"] = pd.to_datetime(data["date"])
    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    return data.dropna(subset=["value"])


def _latest(group: pd.DataFrame, as_of: str):
    if as_of != "latest":
        group = group[group["date"] <= pd.to_datetime(as_of)]
    if group.empty:
        return None
    return group.iloc[-1]


def _bps_change_from(group: pd.DataFrame, latest_date: pd.Timestamp, days: int) -> float | None:
    anchor = group[group["date"] <= latest_date - pd.Timedelta(days=max(days, 0))]
    if anchor.empty:
        return None
    return (group[group["date"] <= latest_date].iloc[-1].value - anchor.iloc[-1].value) * 100
