"""HKMA official API fetcher."""

from __future__ import annotations

from datetime import date
import re
from typing import Any

import pandas as pd

from dashboard.utils.cache import load_metric_cache, save_metric_cache
from dashboard.utils.http import get_json
from dashboard.utils.sanitize import sanitize


HIBOR_URL = "https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hk-interbank-ir-daily"
MONETARY_BASE_URL = "https://api.hkma.gov.hk/public/market-data-and-statistics/daily-monetary-statistics/daily-figures-monetary-base"
INTERBANK_LIQUIDITY_URL = "https://api.hkma.gov.hk/public/market-data-and-statistics/daily-monetary-statistics/daily-figures-interbank-liquidity"

HIBOR_FIELDS = {
    "hibor_on": "ir_overnight",
    "hibor_1w": "ir_1w",
    "hibor_1m": "ir_1m",
    "hibor_3m": "ir_3m",
    "hibor_6m": "ir_6m",
    "hibor_12m": "ir_12m",
}
HIBOR_LIQUIDITY_FALLBACK_FIELDS = {
    "hibor_on": "hibor_overnight",
    "hibor_1m": "hibor_fixing_1m",
}
STANDARD_COLUMNS = ["date", "metric_id", "value", "source", "provider", "as_of_date", "source_status"]


def fetch(metrics: list[dict[str, Any]], as_of: str = "latest") -> tuple[pd.DataFrame, list[str]]:
    hkma_metrics = [m for m in metrics if m["provider"] == "hkma"]
    if not hkma_metrics:
        return _empty(), []

    as_of_date = pd.Timestamp.today().normalize() if as_of == "latest" else pd.to_datetime(as_of).normalize()
    frames: list[pd.DataFrame] = []
    issues: list[str] = []
    metric_by_id = {m["metric_id"]: m for m in hkma_metrics}

    hibor_ids = [metric_id for metric_id in HIBOR_FIELDS if metric_id in metric_by_id]
    if hibor_ids:
        try:
            frames.append(_parse_hibor(_fetch_records(HIBOR_URL, {"segment": "hibor.fixing"}), metric_by_id, as_of_date))
        except Exception as exc:
            cached = _cached_metrics(hibor_ids, 10)
            if not cached.empty:
                frames.append(cached)
                issues.append(f"HKMA HIBOR fixing used cache fallback: {sanitize(exc)}")
                cached_ids = set(cached["metric_id"])
                if set(hibor_ids) <= cached_ids:
                    exc = None
            if exc is None:
                pass
            else:
                try:
                    fallback = _parse_hibor_liquidity_fallback(
                        _fetch_records(INTERBANK_LIQUIDITY_URL, {}),
                        metric_by_id,
                        as_of_date,
                    )
                    frames.append(fallback)
                    issues.append(f"HKMA HIBOR fixing unavailable; partial fallback only: {sanitize(exc)}")
                except Exception as fallback_exc:
                    issues.append(f"HKMA HIBOR fetch failed: {sanitize(exc)}; fallback failed: {sanitize(fallback_exc)}")

    if "hkma_aggregate_balance" in metric_by_id:
        try:
            records = _fetch_records(MONETARY_BASE_URL, {})
            frames.append(
                _parse_aggregate_balance(
                    records,
                    metric_by_id["hkma_aggregate_balance"],
                    as_of_date,
                    "monetary base",
                )
            )
        except Exception as exc:
            cached = load_metric_cache("hkma_aggregate_balance", 10)
            if not cached.empty:
                frames.append(cached)
                issues.append(f"hkma_aggregate_balance used cache fallback: {sanitize(exc)}")
            else:
                try:
                    records = _fetch_records(INTERBANK_LIQUIDITY_URL, {})
                    frames.append(
                        _parse_aggregate_balance(
                            records,
                            metric_by_id["hkma_aggregate_balance"],
                            as_of_date,
                            "interbank liquidity",
                        )
                    )
                    issues.append(f"HKMA monetary base aggregate balance unavailable; used interbank liquidity fallback: {sanitize(exc)}")
                except Exception as fallback_exc:
                    issues.append(f"HKMA aggregate balance fetch failed: {sanitize(exc)}; fallback failed: {sanitize(fallback_exc)}")

    data = pd.concat([frame for frame in frames if not frame.empty], ignore_index=True) if frames else _empty()
    if not data.empty:
        save_metric_cache(data[data.get("source_status", "live") != "cache_fallback"] if "source_status" in data else data)
    return _normalize(data), issues


def _fetch_records(url: str, params: dict[str, Any], page_size: int = 100, max_pages: int = 40) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    offset = 0
    headers = {"Accept": "application/json", "User-Agent": "weekly-financial-dashboard/0.1"}
    while offset < page_size * max_pages:
        request_params = {**params, "offset": offset}
        payload = get_json(url, params=request_params, headers=headers, timeout=30)
        result = payload.get("result") if isinstance(payload, dict) else None
        page_records = (result or {}).get("records") if isinstance(result, dict) else payload.get("records", [])
        if not isinstance(page_records, list):
            raise ValueError("HKMA JSON did not contain a records list.")
        records.extend(page_records)
        datasize = (result or {}).get("datasize") if isinstance(result, dict) else None
        if not page_records or (datasize is not None and len(records) >= int(datasize)):
            break
        offset += len(page_records)
    return records


def _cached_metrics(metric_ids: list[str], max_age_days: int) -> pd.DataFrame:
    frames = [load_metric_cache(metric_id, max_age_days) for metric_id in metric_ids]
    frames = [frame for frame in frames if not frame.empty]
    return pd.concat(frames, ignore_index=True) if frames else _empty()


def _parse_hibor(records: list[dict[str, Any]], metrics: dict[str, dict[str, Any]], as_of_date: pd.Timestamp) -> pd.DataFrame:
    rows = []
    for record in records:
        obs_date = _record_date(record, ["end_of_day", "end_of_date", "date"])
        if obs_date is None or obs_date > as_of_date:
            continue
        for metric_id, field in HIBOR_FIELDS.items():
            if metric_id not in metrics:
                continue
            value = _number(record.get(field))
            if value is None:
                continue
            rows.append(_row(obs_date, metric_id, value, metrics[metric_id], as_of_date))
    return pd.DataFrame(rows, columns=STANDARD_COLUMNS)


def _parse_aggregate_balance(
    records: list[dict[str, Any]],
    metric: dict[str, Any],
    as_of_date: pd.Timestamp,
    source_label: str = "monetary base",
) -> pd.DataFrame:
    rows = []
    available_keys: set[str] = set()
    for record in records:
        available_keys.update(str(key) for key in record)
        obs_date = _record_date(record, ["end_of_date", "end_of_day", "date"])
        if obs_date is None or obs_date > as_of_date:
            continue
        field = _aggregate_balance_field(record)
        value = _number(record.get(field)) if field else None
        if value is not None:
            rows.append(_row(obs_date, "hkma_aggregate_balance", value, metric, as_of_date))
    if not rows:
        keys = ", ".join(sorted(available_keys)) or "none"
        raise ValueError(f"No aggregate balance field found in HKMA {source_label} records. Available keys: {keys}")
    return pd.DataFrame(rows, columns=STANDARD_COLUMNS)


def _parse_hibor_liquidity_fallback(records: list[dict[str, Any]], metrics: dict[str, dict[str, Any]], as_of_date: pd.Timestamp) -> pd.DataFrame:
    rows = []
    for record in records:
        obs_date = _record_date(record, ["end_of_date", "end_of_day", "date"])
        if obs_date is None or obs_date > as_of_date:
            continue
        for metric_id, field in HIBOR_LIQUIDITY_FALLBACK_FIELDS.items():
            if metric_id not in metrics:
                continue
            value = _number(record.get(field))
            if value is not None:
                rows.append(_row(obs_date, metric_id, value, metrics[metric_id], as_of_date))
    return pd.DataFrame(rows, columns=STANDARD_COLUMNS)


def _parse_interbank_liquidity(records: list[dict[str, Any]], metric: dict[str, Any], as_of_date: pd.Timestamp) -> pd.DataFrame:
    rows = []
    for record in records:
        obs_date = _record_date(record, ["end_of_date", "end_of_day", "date"])
        if obs_date is None or obs_date > as_of_date:
            continue
        value = _first_number(record, ["closing_balance", "opening_balance"])
        if value is not None:
            rows.append(_row(obs_date, "hkma_aggregate_balance", value, metric, as_of_date))
    return pd.DataFrame(rows, columns=STANDARD_COLUMNS)


def _aggregate_balance_field(record: dict[str, Any]) -> str | None:
    candidates = [
        key
        for key in record
        if ("aggregate" in _field_key(key) and "balance" in _field_key(key))
        or _field_key(key).startswith("aggrbalance")
    ]
    if not candidates:
        candidates = [
            key
            for key in record
            if _field_key(key) in {"closingbalance", "openingbalance"}
            or _field_key(key).startswith("forecastaggregatebal")
        ]
    if not candidates:
        return None

    def score(key: str) -> tuple[int, str]:
        normalized = _field_key(key)
        points = 0
        if "closing" in normalized or "afdiscwin" in normalized or "afterdiscountwindow" in normalized:
            points += 30
        if "aggregate" in normalized or "aggr" in normalized:
            points += 20
        if "balance" in normalized or "bal" in normalized:
            points += 20
        if "forecast" in normalized or "intraday" in normalized:
            points -= 20
        if "bfdiscwin" in normalized or "beforediscountwindow" in normalized:
            points -= 5
        return points, key

    return max(candidates, key=score)


def _field_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _row(obs_date: pd.Timestamp, metric_id: str, value: float, metric: dict[str, Any], as_of_date: pd.Timestamp) -> dict[str, Any]:
    return {
        "date": obs_date.date(),
        "metric_id": metric_id,
        "value": value,
        "source": metric["source"],
        "provider": metric["provider"],
        "as_of_date": as_of_date.date().isoformat(),
        "source_status": "live",
    }


def _record_date(record: dict[str, Any], fields: list[str]) -> pd.Timestamp | None:
    for field in fields:
        if record.get(field):
            return pd.to_datetime(record[field]).normalize()
    return None


def _first_number(record: dict[str, Any], fields: list[str]) -> float | None:
    for field in fields:
        value = _number(record.get(field))
        if value is not None:
            return value
    return None


def _number(value: Any) -> float | None:
    if value in (None, "", "N/A", "-"):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"(?i)hk\$|hkd|mn|million|\s", "", text)
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return _empty()
    data = df.copy()
    data["date"] = pd.to_datetime(data["date"]).dt.date
    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    return data.dropna(subset=["value"]).drop_duplicates(["date", "metric_id"], keep="last")


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=STANDARD_COLUMNS)
