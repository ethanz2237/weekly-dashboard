"""Source validation checks and markdown report."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from dashboard.config import ROOT
from dashboard.utils.sanitize import sanitize


REPORT_PATH = ROOT / "output" / "source_validation_report.md"


def missing_series(df: pd.DataFrame, metrics: list[dict[str, Any]]) -> list[str]:
    present = set() if df.empty else set(df["metric_id"].unique())
    return [
        m["metric_id"]
        for m in metrics
        if m.get("implemented", True) and m["metric_id"] not in present
    ]


def present_implemented_series(df: pd.DataFrame, metrics: list[dict[str, Any]]) -> list[str]:
    present = set() if df.empty else set(df["metric_id"].unique())
    return [
        m["metric_id"]
        for m in metrics
        if m.get("implemented", True) and m["metric_id"] in present
    ]


def cache_fallback_series(df: pd.DataFrame, metrics: list[dict[str, Any]]) -> list[str]:
    if df.empty or "source_status" not in df:
        return []
    cache = set(df.loc[df["source_status"] == "cache_fallback", "metric_id"].unique())
    return [m["metric_id"] for m in metrics if m.get("implemented", True) and m["metric_id"] in cache]


def planned_unimplemented(metrics: list[dict[str, Any]]) -> list[str]:
    return [
        m["metric_id"]
        for m in metrics
        if not m.get("implemented", True) and not m.get("premium_required") and not m.get("deprecated")
    ]


def premium_required(metrics: list[dict[str, Any]]) -> list[str]:
    return [m["metric_id"] for m in metrics if m.get("premium_required") and not m.get("deprecated")]


def deprecated_metrics(metrics: list[dict[str, Any]]) -> list[str]:
    return [m["metric_id"] for m in metrics if m.get("deprecated")]


def stale_series(df: pd.DataFrame, max_age_days: int = 10) -> list[str]:
    if df.empty:
        return []
    data = df.copy()
    data["date"] = pd.to_datetime(data["date"])
    today = pd.Timestamp.today().normalize()
    stale: list[str] = []
    for metric_id, group in data.groupby("metric_id"):
        latest = group["date"].max().normalize()
        if (today - latest).days > max_age_days:
            stale.append(str(metric_id))
    return stale


def empty_dataframe_issue(df: pd.DataFrame, label: str) -> list[str]:
    return [f"{label} returned an empty DataFrame."] if df.empty else []


def missing_credentials(metrics: list[dict[str, Any]], environ: dict[str, str]) -> list[str]:
    needs_fred = any(m["provider"] == "fred" for m in metrics)
    return ["FRED_API_KEY"] if needs_fred and not environ.get("FRED_API_KEY") else []


def write_report(
    df: pd.DataFrame,
    metrics: list[dict[str, Any]],
    issues: list[str],
    path: Path = REPORT_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    present = present_implemented_series(df, metrics)
    missing = missing_series(df, metrics)
    cache_fallback = cache_fallback_series(df, metrics)
    planned = planned_unimplemented(metrics)
    premium = premium_required(metrics)
    deprecated = deprecated_metrics(metrics)
    stale = stale_series(df)
    unique_issues = list(dict.fromkeys(sanitize(issue) for issue in issues))
    lines = [
        "# Source Validation Report",
        "",
        f"- Rows fetched: {len(df)}",
        f"- Metrics in catalog: {len(metrics)}",
        f"- Implemented and present: {len(present)}",
        f"- Implemented but missing: {len(missing)}",
        f"- Present via cache fallback: {len(cache_fallback)}",
        f"- Planned but not implemented: {len(planned)}",
        f"- Premium required: {len(premium)}",
        f"- Deprecated: {len(deprecated)}",
        "",
        "## Implemented And Present",
        *(f"- {item}" for item in present),
        "None" if not present else "",
        "",
        "## Implemented But Missing",
        *(f"- {item}" for item in missing),
        "None" if not missing else "",
        "",
        "## Present Via Cache Fallback",
        *(f"- {item}" for item in cache_fallback),
        "None" if not cache_fallback else "",
        "",
        "## Planned But Not Implemented",
        *(f"- {item}" for item in planned),
        "None" if not planned else "",
        "",
        "## Premium Required",
        *(f"- {item}" for item in premium),
        "None" if not premium else "",
        "",
        "## Deprecated",
        *(f"- {item}" for item in deprecated),
        "None" if not deprecated else "",
        "",
        "## Stale Series",
        *(f"- {item}" for item in stale),
        "None" if not stale else "",
        "",
        "## Source Issues",
        *(f"- {item}" for item in unique_issues),
        "None" if not unique_issues else "",
        "",
    ]
    path.write_text("\n".join(line for line in lines if line != "") + "\n")
    return path
