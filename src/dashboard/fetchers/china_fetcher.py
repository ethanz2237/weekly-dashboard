"""Manual China rates CSV fallback."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from dashboard.config import ROOT
from dashboard.utils.cache import load_metric_cache, save_metric_cache
from dashboard.utils.sanitize import sanitize


MANUAL_CHINA_RATES = ROOT / "data" / "manual" / "china_rates.csv"


def fetch(metrics: list[dict[str, Any]], as_of: str = "latest") -> tuple[pd.DataFrame, list[str]]:
    china_metrics = [m for m in metrics if m.get("provider") == "manual_china" and m.get("implemented")]
    if not china_metrics:
        return _empty(), []
    end = date.today().isoformat() if as_of == "latest" else as_of
    issues: list[str] = []
    try:
        manual = read_manual_csv(MANUAL_CHINA_RATES, end)
    except Exception as exc:
        manual = pd.DataFrame()
        issues.append(f"China manual CSV failed: {sanitize(exc)}")

    frames = []
    for metric in china_metrics:
        frame = manual[manual["metric_id"] == metric["metric_id"]].copy() if not manual.empty else pd.DataFrame()
        if frame.empty:
            cached = load_metric_cache(metric["metric_id"], 10)
            if not cached.empty:
                frames.append(cached)
                issues.append(f"{metric['metric_id']} used cache fallback after China manual CSV issue.")
            else:
                issues.append(f"{metric['metric_id']}: no China manual CSV observations available.")
            continue
        frame["source"] = frame.get("source", metric["source"]).fillna(metric["source"])
        frame["provider"] = frame.get("provider", metric["provider"]).fillna(metric["provider"])
        frame["as_of_date"] = end
        frame["source_status"] = "manual"
        save_metric_cache(frame)
        frames.append(frame)
    return _normalize(pd.concat(frames, ignore_index=True) if frames else _empty()), issues


def read_manual_csv(path: Path = MANUAL_CHINA_RATES, as_of: str = "latest") -> pd.DataFrame:
    if not path.exists():
        return _empty()
    data = pd.read_csv(path)
    if data.empty or not {"date", "metric_id", "value"} <= set(data.columns):
        return _empty()
    data = data.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    end = pd.Timestamp.today().normalize() if as_of == "latest" else pd.to_datetime(as_of)
    data = data[data["date"] <= end]
    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    data["source"] = data.get("source", "manual_csv")
    data["provider"] = data.get("provider", "manual_china")
    data["as_of_date"] = str(end.date())
    return data[["date", "metric_id", "value", "source", "provider", "as_of_date"]].dropna(subset=["date", "value"])


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "metric_id", "value", "source", "provider", "as_of_date", "source_status"])


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return _empty()
    data = df.copy()
    data["date"] = pd.to_datetime(data["date"]).dt.date
    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    return data.dropna(subset=["value"])
