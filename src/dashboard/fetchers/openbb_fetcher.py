"""Optional OpenBB fetcher.

This MVP keeps OpenBB non-blocking. Real OpenBB provider calls can be added
metric by metric once the installed extensions and credentials are known.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def fetch(metrics: list[dict[str, Any]], as_of: str = "latest") -> tuple[pd.DataFrame, list[str]]:
    try:
        import openbb  # noqa: F401
    except Exception as exc:
        return _empty(), [f"OpenBB unavailable; skipped optional fetcher: {exc}"]
    return _empty(), ["OpenBB optional fetcher loaded; no MVP metrics assigned to OpenBB yet."]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "metric_id", "value", "source", "provider", "as_of_date"])
