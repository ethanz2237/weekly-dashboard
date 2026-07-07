"""ECB Data Portal CSV fetcher."""

from __future__ import annotations

from datetime import date
from io import StringIO
from typing import Any

import pandas as pd

from dashboard.utils.cache import load_metric_cache, save_metric_cache
from dashboard.utils.http import get_text
from dashboard.utils.sanitize import sanitize


ECB_DATA_URL = "https://data-api.ecb.europa.eu/service/data"


def fetch(metrics: list[dict[str, Any]], as_of: str = "latest") -> tuple[pd.DataFrame, list[str]]:
    ecb_metrics = [m for m in metrics if m.get("provider") == "ecb" and m.get("implemented")]
    if not ecb_metrics:
        return _empty(), []

    frames: list[pd.DataFrame] = []
    issues: list[str] = []
    end = date.today().isoformat() if as_of == "latest" else as_of

    for metric in ecb_metrics:
        path = str(metric.get("ticker_or_series", ""))
        try:
            text = get_text(f"{ECB_DATA_URL}/{path}", params={"startPeriod": "2020-01-01", "endPeriod": end, "format": "csvdata"}, timeout=30)
            frame = _parse_csv(text, metric, end)
        except Exception as exc:
            frame = pd.DataFrame()
            issue = f"{metric['metric_id']}: ECB fetch failed: {sanitize(exc)}"
        else:
            issue = ""

        if frame.empty:
            cached = load_metric_cache(metric["metric_id"], 10)
            if not cached.empty:
                frames.append(cached)
                issues.append(f"{metric['metric_id']} used cache fallback" + (f" due to ECB error: {issue}" if issue else "."))
            else:
                issues.append(issue or f"{metric['metric_id']}: ECB returned no usable observations.")
            continue

        frame["source_status"] = "live"
        save_metric_cache(frame)
        frames.append(frame)

    return _normalize(pd.concat(frames, ignore_index=True) if frames else _empty()), issues


def _parse_csv(text: str, metric: dict[str, Any], end: str) -> pd.DataFrame:
    data = pd.read_csv(StringIO(text))
    if not {"TIME_PERIOD", "OBS_VALUE"} <= set(data.columns):
        return _empty()
    rows = data[["TIME_PERIOD", "OBS_VALUE"]].rename(columns={"TIME_PERIOD": "date", "OBS_VALUE": "value"})
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
