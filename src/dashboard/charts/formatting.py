"""Chart value formatting helpers."""

from __future__ import annotations

import math
from typing import Any


def format_value(value: Any, style: str = "level") -> str:
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return ""
    if style == "percent":
        return f"{number:.2f}%"
    if style == "bps":
        return f"{number:+.0f}bp"
    if style == "money_hkd_mn":
        return f"HK${number / 1000:.1f}bn"
    if style == "usd_billions":
        return f"${number:,.0f}bn"
    if style == "usd_millions":
        return f"${number / 1000:,.0f}bn"
    if style == "integer":
        return f"{number:,.0f}"
    if style == "raw":
        return str(value)
    return f"{number:,.2f}" if abs(number) < 100 else f"{number:,.0f}"


def infer_format(title: str = "", unit: str | None = None) -> str:
    text = f"{title} {unit or ''}".lower()
    if "hkd mn" in text or "hkd_million" in text or "aggregate balance" in text:
        return "money_hkd_mn"
    if "spread" in text or "bps" in text or " bp" in text:
        return "bps"
    if "yield" in text or "rate" in text or "corridor" in text or "hibor" in text or "percent" in text:
        return "percent"
    if "index" in text or "normalized" in text:
        return "integer"
    return "level"
