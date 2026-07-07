"""Japan MOF JGB interest-rate CSV fetcher."""

from __future__ import annotations

from datetime import date
from io import StringIO
from typing import Any

import pandas as pd

from dashboard.utils.cache import load_metric_cache, save_metric_cache
from dashboard.utils.http import get_text
from dashboard.utils.sanitize import sanitize


JGB_RATES_URL = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv"


def fetch(metrics: list[dict[str, Any]], as_of: str = "latest") -> tuple[pd.DataFrame, list[str]]:
    mof_metrics = [m for m in metrics if m.get("provider") == "mof" and m.get("implemented")]
    if not mof_metrics:
        return _empty(), []
    end = date.today().isoformat() if as_of == "latest" else as_of
    issues: list[str] = []
    try:
        table = _read_rates(get_text(JGB_RATES_URL, timeout=30), end)
    except Exception as exc:
        table = pd.DataFrame()
        issues.append(f"MOF JGB fetch failed: {sanitize(exc)}")

    frames = []
    for metric in mof_metrics:
        frame = _metric_frame(table, metric, end)
        if frame.empty:
            cached = load_metric_cache(metric["metric_id"], 10)
            if not cached.empty:
                frames.append(cached)
                issues.append(f"{metric['metric_id']} used cache fallback after MOF fetch issue.")
            else:
                issues.append(f"{metric['metric_id']}: MOF returned no usable observations.")
            continue
        frame["source_status"] = "live"
        save_metric_cache(frame)
        frames.append(frame)
    return _normalize(pd.concat(frames, ignore_index=True) if frames else _empty()), issues


def _read_rates(text: str, end: str) -> pd.DataFrame:
    data = pd.read_csv(StringIO(text), skiprows=1, na_values=["-", ""])
    if "Date" not in data:
        return pd.DataFrame()
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data = data[(data["Date"] >= "2020-01-01") & (data["Date"] <= pd.to_datetime(end))]
    return data


def _metric_frame(table: pd.DataFrame, metric: dict[str, Any], end: str) -> pd.DataFrame:
    tenor = str(metric.get("ticker_or_series", ""))
    if table.empty or tenor not in table:
        return _empty()
    rows = table[["Date", tenor]].rename(columns={"Date": "date", tenor: "value"})
    rows["metric_id"] = metric["metric_id"]
    rows["source"] = metric["source"]
    rows["provider"] = metric["provider"]
    rows["as_of_date"] = end
    return rows[["date", "metric_id", "value", "source", "provider", "as_of_date"]]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "metric_id", "value", "source", "provider", "as_of_date", "source_status"])


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return _empty()
    data = df.copy()
    data["date"] = pd.to_datetime(data["date"]).dt.date
    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    return data.dropna(subset=["value"])
