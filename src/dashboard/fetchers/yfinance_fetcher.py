"""yfinance data fetcher."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import yfinance as yf

from dashboard.utils.cache import load_metric_cache, save_metric_cache


def fetch(metrics: list[dict[str, Any]], as_of: str = "latest") -> tuple[pd.DataFrame, list[str]]:
    yf_metrics = [m for m in metrics if m["provider"] == "yfinance"]
    frames: list[pd.DataFrame] = []
    issues: list[str] = []
    end = None if as_of == "latest" else as_of

    for metric in yf_metrics:
        frame, ticker_issues = _fetch_metric(metric, end, as_of)
        if not frame.empty:
            frames.append(frame)
            continue
        cached = load_metric_cache(metric["metric_id"], 10)
        if not cached.empty:
            frames.append(cached)
            issues.append(f"{metric['metric_id']} used cache fallback after yfinance failures: {'; '.join(ticker_issues)}")
        else:
            issues.extend(ticker_issues)

    if not frames:
        return _empty(), issues
    return pd.concat(frames, ignore_index=True), issues


def _fetch_metric(metric: dict[str, Any], end: str | None, as_of: str) -> tuple[pd.DataFrame, list[str]]:
    issues = []
    for ticker in _tickers(metric["ticker_or_series"]):
        try:
            data = yf.download(ticker, start="2020-01-01", end=end, progress=False, auto_adjust=False, threads=False)
        except Exception as exc:
            issues.append(f"{metric['metric_id']} {ticker}: yfinance fetch failed: {exc}")
            continue
        if data.empty:
            issues.append(f"{metric['metric_id']} {ticker}: yfinance returned no rows.")
            continue
        series = _price_series(data)
        if series.empty:
            issues.append(f"{metric['metric_id']} {ticker}: yfinance returned no price column.")
            continue
        rows = pd.DataFrame(
            {
                "date": pd.to_datetime(series.index).date,
                "metric_id": metric["metric_id"],
                "value": pd.to_numeric(series.values, errors="coerce"),
                "source": metric["source"],
                "provider": metric["provider"],
                "as_of_date": date.today().isoformat() if as_of == "latest" else as_of,
                "ticker_used": ticker,
                "source_status": "live",
            }
        ).dropna(subset=["value"])
        if not rows.empty:
            save_metric_cache(rows)
            return rows, issues
    return _empty(), issues


def _tickers(value: Any) -> list[str]:
    return value if isinstance(value, list) else [value]


def _price_series(data: pd.DataFrame) -> pd.Series:
    if isinstance(data.columns, pd.MultiIndex):
        for name in ("Adj Close", "Close"):
            if name in data.columns.get_level_values(0):
                return data[name].iloc[:, 0]
    for name in ("Adj Close", "Close"):
        if name in data:
            return data[name]
    return pd.Series(dtype=float)


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "metric_id", "value", "source", "provider", "as_of_date", "ticker_used", "source_status"])
