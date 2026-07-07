"""Price-like return transforms."""

from __future__ import annotations

import pandas as pd


WINDOWS = {"1W": 7, "1M": 30, "3M": 91, "6M": 182}


def calculate_price_returns(df: pd.DataFrame, as_of: str = "latest") -> pd.DataFrame:
    rows = []
    for metric_id, group in _prepared(df).groupby("metric_id"):
        group = group.sort_values("date")
        latest = _latest_on_or_before(group, as_of)
        if latest is None:
            continue
        row = {"metric_id": metric_id, "latest_level": latest.value, "latest_date": latest.date}
        for label, days in WINDOWS.items():
            row[f"{label}_return_pct"] = _pct_change_from(group, latest.date, days)
        ytd_days = (latest.date - pd.Timestamp(year=latest.date.year, month=1, day=1)).days
        row["YTD_return_pct"] = _pct_change_from(group, latest.date, ytd_days)
        rows.append(row)
    return pd.DataFrame(rows)


def _prepared(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    data = df.copy()
    data["date"] = pd.to_datetime(data["date"])
    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    return data.dropna(subset=["value"])


def _latest_on_or_before(group: pd.DataFrame, as_of: str):
    if as_of != "latest":
        group = group[group["date"] <= pd.to_datetime(as_of)]
    if group.empty:
        return None
    return group.iloc[-1]


def _pct_change_from(group: pd.DataFrame, latest_date: pd.Timestamp, days: int) -> float | None:
    if days <= 0:
        anchor_group = group[group["date"] <= latest_date]
    else:
        anchor_group = group[group["date"] <= latest_date - pd.Timedelta(days=days)]
    if anchor_group.empty:
        return None
    old = anchor_group.iloc[-1].value
    new = group[group["date"] <= latest_date].iloc[-1].value
    if old == 0:
        return None
    return (new / old - 1) * 100
