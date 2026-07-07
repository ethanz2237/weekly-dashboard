"""FRED data fetcher."""

from __future__ import annotations

import os
from datetime import date
from typing import Any

import pandas as pd

from dashboard.utils.cache import load_metric_cache, save_metric_cache
from dashboard.utils.http import get_json
from dashboard.utils.sanitize import sanitize


FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"


def fetch(metrics: list[dict[str, Any]], as_of: str = "latest") -> tuple[pd.DataFrame, list[str]]:
    api_key = os.getenv("FRED_API_KEY")
    fred_metrics = [m for m in metrics if m["provider"] == "fred"]
    if not fred_metrics:
        return _empty(), []
    if not api_key:
        return _empty(), ["FRED_API_KEY is missing; skipped FRED metrics."]

    frames: list[pd.DataFrame] = []
    issues: list[str] = []
    end = date.today().isoformat() if as_of == "latest" else as_of
    start = "2020-01-01"

    for metric in fred_metrics:
        params = {
            "series_id": metric["ticker_or_series"],
            "api_key": api_key,
            "file_type": "json",
            "observation_start": start,
            "observation_end": end,
        }
        try:
            observations = get_json(FRED_OBSERVATIONS_URL, params=params, timeout=30).get("observations", [])
        except Exception as exc:
            cached = load_metric_cache(metric["metric_id"], _max_age(metric))
            if not cached.empty:
                frames.append(cached)
                issues.append(f"{metric['metric_id']} used cache fallback due to FRED error: {sanitize(exc)}")
            else:
                issues.append(f"{metric['metric_id']}: FRED fetch failed: {sanitize(exc)}")
            continue

        rows = [
            {
                "date": item["date"],
                "metric_id": metric["metric_id"],
                "value": item["value"],
                "source": metric["source"],
                "provider": metric["provider"],
                "as_of_date": date.today().isoformat() if as_of == "latest" else as_of,
            }
            for item in observations
            if item.get("value") not in (None, ".")
        ]
        if rows:
            frame = pd.DataFrame(rows)
            frame["source_status"] = "live"
            save_metric_cache(frame)
            frames.append(frame)
        else:
            cached = load_metric_cache(metric["metric_id"], _max_age(metric))
            if not cached.empty:
                frames.append(cached)
                issues.append(f"{metric['metric_id']} used cache fallback because FRED returned no usable observations.")
            else:
                issues.append(f"{metric['metric_id']}: FRED returned no usable observations.")

    return _normalize(pd.concat(frames, ignore_index=True) if frames else _empty()), issues


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "metric_id", "value", "source", "provider", "as_of_date", "source_status"])


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return _empty()
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["value"])


def _max_age(metric: dict[str, Any]) -> int:
    return 14 if metric.get("frequency") == "weekly" else 10
