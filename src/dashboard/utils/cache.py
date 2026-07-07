"""Data cache helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from dashboard.config import ROOT


RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
CACHE_DIR = RAW_DIR / "metric_cache"


def save_raw(df: pd.DataFrame, name: str) -> Path:
    return _save(df, RAW_DIR, name)


def save_processed(df: pd.DataFrame, name: str) -> Path:
    return _save(df, PROCESSED_DIR, name)


def save_metric_cache(df: pd.DataFrame) -> None:
    if df.empty or "metric_id" not in df:
        return
    for metric_id, group in df.groupby("metric_id"):
        _save(group, CACHE_DIR, str(metric_id))


def load_metric_cache(metric_id: str, max_age_days: int = 10) -> pd.DataFrame:
    path = _cache_path(metric_id)
    if path is None:
        return pd.DataFrame()
    data = _read(path)
    if data.empty or "date" not in data:
        return pd.DataFrame()
    latest = pd.to_datetime(data["date"]).max().normalize()
    if (pd.Timestamp.today().normalize() - latest).days > max_age_days:
        return pd.DataFrame()
    data = data.copy()
    data["source_status"] = "cache_fallback"
    return data


def cache_available(metric_ids: list[str] | set[str], max_age_days: int = 10) -> bool:
    return any(not load_metric_cache(metric_id, max_age_days).empty for metric_id in metric_ids)


def _save(df: pd.DataFrame, directory: Path, name: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    parquet_path = directory / f"{name}.parquet"
    try:
        df.to_parquet(parquet_path, index=False)
        return parquet_path
    except Exception:
        csv_path = directory / f"{name}.csv"
        df.to_csv(csv_path, index=False)
        return csv_path


def _cache_path(metric_id: str) -> Path | None:
    for suffix in ("parquet", "csv"):
        path = CACHE_DIR / f"{metric_id}.{suffix}"
        if path.exists():
            return path
    return None


def _read(path: Path) -> pd.DataFrame:
    try:
        return pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
    except Exception:
        return pd.DataFrame()
