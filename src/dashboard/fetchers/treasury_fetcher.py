"""Treasury FiscalData auction fetcher."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from dashboard.utils.cache import load_metric_cache, save_metric_cache
from dashboard.utils.http import get_json
from dashboard.utils.sanitize import sanitize


AUCTIONS_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
STANDARD_COLUMNS = ["date", "metric_id", "value", "source", "provider", "as_of_date"]
AUCTION_TYPES = {"Bill", "Note", "Bond", "FRN", "TIPS"}


def fetch(metrics: list[dict[str, Any]], as_of: str = "latest") -> tuple[pd.DataFrame, list[str]]:
    treasury_metrics = [m for m in metrics if m["provider"] == "treasury"]
    implemented = {m["metric_id"]: m for m in treasury_metrics if m.get("implemented", True)}
    if not implemented:
        return _empty(), []

    as_of_date = pd.Timestamp.today().normalize() if as_of == "latest" else pd.to_datetime(as_of).normalize()
    try:
        records = _fetch_records(as_of_date)
    except Exception as exc:
        cached = _cached_metrics(list(implemented), 60)
        if not cached.empty:
            return cached, [f"Treasury FiscalData used cache fallback: {sanitize(exc)}"]
        return _empty(), [f"Treasury FiscalData auction fetch failed: {sanitize(exc)}"]

    frame = _parse_auctions(records, implemented, as_of_date)
    if not frame.empty:
        save_metric_cache(frame)
    issues = [] if not frame.empty else ["Treasury FiscalData returned no completed auction observations."]
    return _normalize(frame), issues


def _fetch_records(as_of_date: pd.Timestamp, page_size: int = 100, max_pages: int = 10) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    page = 1
    headers = {"Accept": "application/json", "User-Agent": "weekly-financial-dashboard/0.1"}
    fields = ",".join(
        [
            "auction_date",
            "security_type",
            "security_term",
            "cusip",
            "offering_amt",
            "currently_outstanding",
            "est_pub_held_mat_by_type_amt",
            "total_accepted",
            "bid_to_cover_ratio",
            "direct_bidder_accepted",
            "indirect_bidder_accepted",
            "primary_dealer_accepted",
        ]
    )
    while page <= max_pages:
        params = {
            "fields": fields,
            "filter": f"auction_date:lte:{as_of_date.date()}",
            "sort": "-auction_date",
            "page[number]": page,
            "page[size]": page_size,
        }
        payload = get_json(AUCTIONS_URL, params=params, headers=headers, timeout=30)
        page_records = payload.get("data", [])
        if not isinstance(page_records, list):
            raise ValueError("FiscalData JSON did not contain a data list.")
        records.extend(page_records)
        if len(page_records) < page_size:
            break
        page += 1
    return records


def _parse_auctions(records: list[dict[str, Any]], metrics: dict[str, dict[str, Any]], as_of_date: pd.Timestamp) -> pd.DataFrame:
    rows = []
    for record in records:
        obs_date = pd.to_datetime(record.get("auction_date"), errors="coerce")
        if pd.isna(obs_date) or obs_date.normalize() > as_of_date:
            continue
        security_type = str(record.get("security_type") or "")
        if security_type not in AUCTION_TYPES:
            continue
        total_accepted = _number(record.get("total_accepted")) or _number(record.get("offering_amt"))
        bid_to_cover = _number(record.get("bid_to_cover_ratio"))
        if total_accepted is None and bid_to_cover is None:
            continue
        common = {
            "security_type": security_type,
            "security_term": record.get("security_term"),
            "cusip": record.get("cusip"),
            "offering_amt": _number(record.get("offering_amt")),
            "total_accepted": total_accepted,
        }
        _append(rows, obs_date, "treasury_auction_bid_to_cover", bid_to_cover, metrics, as_of_date, common)
        _append(
            rows,
            obs_date,
            "treasury_auction_net_issuance",
            _net_issuance(record),
            metrics,
            as_of_date,
            common,
        )
        for metric_id, field in [
            ("treasury_auction_direct_bidders", "direct_bidder_accepted"),
            ("treasury_auction_indirect_bidders", "indirect_bidder_accepted"),
            ("treasury_auction_primary_dealer_allocation", "primary_dealer_accepted"),
        ]:
            value = _allocation_pct(record.get(field), total_accepted)
            _append(rows, obs_date, metric_id, value, metrics, as_of_date, common)
    return pd.DataFrame(rows, columns=[*STANDARD_COLUMNS, "source_status", "security_type", "security_term", "cusip", "offering_amt", "total_accepted"])


def _append(
    rows: list[dict[str, Any]],
    obs_date: pd.Timestamp,
    metric_id: str,
    value: float | None,
    metrics: dict[str, dict[str, Any]],
    as_of_date: pd.Timestamp,
    extra: dict[str, Any],
) -> None:
    if metric_id not in metrics or value is None:
        return
    metric = metrics[metric_id]
    rows.append(
        {
            "date": obs_date.date(),
            "metric_id": metric_id,
            "value": value,
            "source": metric["source"],
            "provider": metric["provider"],
            "as_of_date": as_of_date.date().isoformat(),
            "source_status": "live",
            **extra,
        }
    )


def _net_issuance(record: dict[str, Any]) -> float | None:
    offering = _number(record.get("offering_amt"))
    maturity = _number(record.get("est_pub_held_mat_by_type_amt"))
    if offering is None:
        return None
    if maturity is None:
        return offering / 1_000_000_000
    return (offering - maturity) / 1_000_000_000


def _allocation_pct(value: Any, total: float | None) -> float | None:
    amount = _number(value)
    if amount is None or not total:
        return None
    return amount / total * 100


def _number(value: Any) -> float | None:
    if value in (None, "", "null", "N/A"):
        return None
    try:
        return float(str(value).replace(",", "").replace("$", ""))
    except ValueError:
        return None


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return _empty()
    data = df.copy()
    data["date"] = pd.to_datetime(data["date"]).dt.date
    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    return data.dropna(subset=["value"])


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=[*STANDARD_COLUMNS, "source_status"])


def _cached_metrics(metric_ids: list[str], max_age_days: int) -> pd.DataFrame:
    frames = [load_metric_cache(metric_id, max_age_days) for metric_id in metric_ids]
    frames = [frame for frame in frames if not frame.empty]
    return pd.concat(frames, ignore_index=True) if frames else _empty()
