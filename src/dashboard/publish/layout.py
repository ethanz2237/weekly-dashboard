"""Dashboard layout assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from dashboard.config import ROOT


PERIOD_COLUMNS = [
    "1W_return_pct",
    "1M_return_pct",
    "3M_return_pct",
    "6M_return_pct",
    "YTD_return_pct",
    "1W_change_bps",
    "1M_change_bps",
    "3M_change_bps",
    "6M_change_bps",
    "YTD_change_bps",
]


def build_dashboard_layout(
    raw: pd.DataFrame,
    transforms: dict[str, pd.DataFrame],
    all_metrics: list[dict[str, Any]],
    active_metrics: list[dict[str, Any]],
    chart_paths: list[Path],
    validation_report: Path,
    as_of: str = "latest",
    markdown_parent: Path = ROOT / "output",
) -> dict[str, Any]:
    metric_names = {m["metric_id"]: m["display_name"] for m in all_metrics}
    chart_map = {path.name: _rel_to(path, markdown_parent) for path in chart_paths}
    missing = _missing_metrics(raw, active_metrics)
    placeholders = [m for m in all_metrics if m.get("source") == "placeholder"]
    premium = [m for m in all_metrics if m.get("premium_required")]
    as_of_info = _as_of_info(raw, active_metrics, as_of)

    return {
        "title": "Weekly Financial Dashboard",
        "as_of": as_of_info["latest_data_date_overall"],
        "generated_at": as_of_info["generated_at"],
        "requested_as_of": as_of_info["requested_as_of"],
        "latest_data_date_overall": as_of_info["latest_data_date_overall"],
        "latest_data_date_by_asset_class": as_of_info["latest_data_date_by_asset_class"],
        "executive_snapshot": {
            "data_as_of_date": as_of_info["latest_data_date_overall"],
            "generated_at": as_of_info["generated_at"],
            "requested_as_of": as_of_info["requested_as_of"],
            "latest_data_date_by_asset_class": as_of_info["latest_data_date_by_asset_class"],
            "key_cross_asset_moves": _key_moves(transforms, metric_names),
            "top_movers": _top_movers(transforms, metric_names),
            "missing_data_summary": _missing_summary(missing, placeholders, premium),
        },
        "sections": {
            "equity": {
                "global_index_return_table": _records(transforms.get("price_returns"), metric_names),
                "chart": chart_map.get("equity_indices_normalized.png"),
                "global_equity_indices_chart": chart_map.get("global_equity_indices_normalized.png"),
                "global_equity_indices_heatmap": chart_map.get("global_equity_indices_heatmap.png"),
                "factor_proxy_ratios_chart": chart_map.get("factor_proxy_ratios.png"),
                "factor_proxy_table": _latest_metric_records(transforms.get("factor_proxy_ratios"), metric_names),
                "us_sector_heatmap": chart_map.get("us_sector_heatmap.png"),
                "us_sector_table": _records(transforms.get("sector_returns"), metric_names),
                "growth_vs_value": "Implemented as an IWF/IWD ETF price ratio proxy.",
                "cyclicals_vs_defensives": "Implemented as defensive sector ETF basket divided by cyclical sector ETF basket.",
                "sector_heatmap": "Implemented with Select Sector SPDR ETF returns.",
            },
            "rates": {
                "us_treasury_curve_chart": chart_map.get("ust_curve.png"),
                "us_treasury_curve_note": "The UST curve chart uses the full available FRED Treasury tenor ladder; 2Y, 5Y, 10Y, and 30Y are highlighted key tenors, with latest, 1W ago, and 1M ago curves shown.",
                "us_curve_spreads_chart": chart_map.get("ust_curve_spreads.png"),
                "us_curve_spreads_expanded_chart": chart_map.get("us_curve_spreads_expanded.png"),
                "us_money_market_corridor_chart": chart_map.get("us_money_market_corridor.png"),
                "us_liquidity_stack_chart": chart_map.get("us_liquidity_stack.png"),
                "fed_corridor_chart": chart_map.get("fed_corridor.png"),
                "curve_spreads": _latest_records(transforms.get("curve_spreads"), "spread_id", metric_names),
                "us_rate_spreads": _latest_metric_records(transforms.get("us_rate_spreads"), metric_names),
                "money_market_indicators": _filter_records(
                    transforms.get("rate_changes"),
                    {"sofr", "effr", "iorb", "us_3m_tbill_yield", "on_rrp_rate", "on_rrp_usage", "obfr", "tga", "srf_usage", "bank_reserves"},
                    metric_names,
                ),
            },
            "eu_rates": {
                "eu_yield_curve_chart": chart_map.get("eu_yield_curve.png"),
                "ecb_policy_rates_chart": chart_map.get("ecb_policy_rates.png"),
                "eu_yield_curve_note": "The EUR curve chart uses the available ECB euro area yield curve tenor ladder; 2Y, 5Y, 10Y, and 30Y are highlighted key tenors, with latest, 1W ago, and 1M ago curves shown.",
                "policy_rates": _filter_records(
                    transforms.get("rate_changes"),
                    {"eur_on_rate", "ecb_deposit_rate", "ecb_main_refi_rate", "ecb_marginal_lending_rate"},
                    metric_names,
                ),
                "curve_tenors": _filter_records(
                    transforms.get("rate_changes"),
                    {"eur_2y_yield", "eur_5y_yield", "eur_10y_yield", "eur_30y_yield"},
                    metric_names,
                ),
            },
            "treasury_auctions": {
                "auction_calendar_table": _records(transforms.get("treasury_auction_calendar_table"), metric_names),
                "bid_to_cover_chart": chart_map.get("treasury_auction_bid_to_cover.png"),
                "allocation_chart": chart_map.get("treasury_auction_allocation.png"),
                "net_issuance_chart": chart_map.get("treasury_net_issuance.png"),
                "auction_metrics": _latest_filtered_records(
                    raw,
                    {
                        "treasury_auction_net_issuance",
                        "treasury_auction_bid_to_cover",
                        "treasury_auction_direct_bidders",
                        "treasury_auction_indirect_bidders",
                        "treasury_auction_primary_dealer_allocation",
                    },
                    metric_names,
                ),
                "tail_stop_note": "Treasury auction tail / stop-through is intentionally left as a placeholder because FiscalData does not provide when-issued yield.",
            },
            "hk_rates": {
                "hibor_curve_chart": chart_map.get("hk_hibor_curve.png"),
                "hibor_curve_note": "The HIBOR curve chart uses the full available HKMA tenor ladder; O/N, 1M, 3M, and 6M are highlighted key tenors, with latest, 1W ago, and 1M ago curves shown.",
                "hkma_aggregate_balance_chart": chart_map.get("hkma_aggregate_balance.png"),
                "hibor_sofr_spreads_chart": chart_map.get("hibor_sofr_spreads.png"),
                "latest_hibor_tenors": _filter_records(
                    transforms.get("hk_rate_changes"),
                    {"hibor_on", "hibor_1w", "hibor_1m", "hibor_3m", "hibor_6m", "hibor_12m"},
                    metric_names,
                ),
                "hibor_sofr_spreads": _latest_metric_records(transforms.get("hibor_sofr_spreads"), metric_names),
                "notes": "HIBOR-SOFR tenor spreads are MVP proxy spreads using same-date HIBOR minus daily SOFR; they are not matched-tenor HKD/USD OIS spreads.",
            },
            "asia_rates": {
                "jp_jgb_curve_chart": chart_map.get("jp_jgb_curve.png"),
                "jp_jgb_yields_chart": chart_map.get("jp_jgb_yields.png"),
                "jp_jgb_curve_note": "The JGB curve chart uses the available Japan MOF constant-maturity tenor ladder from 1Y through 40Y; 2Y, 5Y, 10Y, and 30Y are highlighted key tenors.",
                "jp_key_yields": _filter_records(
                    transforms.get("rate_changes"),
                    {"jgb_2y", "jgb_5y", "jgb_10y", "jgb_30y"},
                    metric_names,
                ),
            },
            "china_rates": {
                "cn_cgb_curve_chart": chart_map.get("cn_cgb_curve.png"),
                "cn_money_market_rates_chart": chart_map.get("cn_money_market_rates.png"),
                "cn_policy_rates_chart": chart_map.get("cn_policy_rates.png"),
                "manual_csv_note": "China live rates are not scraped. If reliable source data is unavailable, provide observations in data/manual/china_rates.csv using columns date, metric_id, value, source, provider, notes.",
                "cgb_key_yields": _filter_records(
                    transforms.get("rate_changes"),
                    {"cgb_2y", "cgb_5y", "cgb_10y", "cgb_30y"},
                    metric_names,
                ),
                "money_market_rates": _filter_records(transforms.get("rate_changes"), {"dr007", "fr007"}, metric_names),
                "policy_rates": _filter_records(transforms.get("rate_changes"), {"lpr", "mlf", "slf"}, metric_names),
            },
            "credit": {
                "us_ig_hy_spread_chart": chart_map.get("credit_spreads.png"),
                "eu_credit_spreads_chart": chart_map.get("eu_credit_spreads.png"),
                "spread_table": _filter_records(transforms.get("rate_changes"), {"us_ig_oas", "us_hy_oas"}, metric_names),
                "eu_spread_table": _filter_records(transforms.get("rate_changes"), {"eu_ig_oas", "eu_hy_oas"}, metric_names),
            },
            "fx": {
                "fx_spot_table": _records(transforms.get("fx_returns"), metric_names),
                "fx_spot_heatmap": chart_map.get("fx_spot_heatmap.png"),
                "fx_spot_expanded_heatmap": chart_map.get("fx_spot_expanded_heatmap.png"),
                "fx_implied_vol": "Premium-required placeholder; source not implemented yet.",
                "cross_currency_basis": "Premium-required placeholder; source not implemented yet.",
            },
            "cross_market": {
                "yield_differentials_heatmap": chart_map.get("cross_market_yield_differentials_heatmap.png"),
                "yield_differentials_table": _latest_metric_records(
                    transforms.get("cross_market_yield_differentials"),
                    metric_names,
                ),
                "yield_differentials_note": "Yield differentials are calculated only when both legs are available, using local yield minus USD yield in basis points.",
            },
            "missing_premium_required_data": {
                "unavailable_datasets": [_metric_summary(m) for m in placeholders],
                "premium_required_datasets": [_metric_summary(m) for m in premium],
            },
            "source_validation_summary": _validation_summary(validation_report),
        },
    }


def _records(df: pd.DataFrame | None, metric_names: dict[str, str] | None = None) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    data = df.copy()
    if metric_names and "metric_id" in data:
        names = data["metric_id"].map(metric_names).fillna(data["metric_id"])
        if "display_name" in data:
            data["display_name"] = data["display_name"].fillna(names)
        else:
            data.insert(1, "display_name", names)
    for col in data.columns:
        if pd.api.types.is_datetime64_any_dtype(data[col]):
            data[col] = data[col].dt.strftime("%Y-%m-%d")
    return data.where(pd.notna(data), None).to_dict(orient="records")


def _filter_records(
    df: pd.DataFrame | None,
    metric_ids: set[str],
    metric_names: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    if df is None or df.empty or "metric_id" not in df:
        return []
    return _records(df[df["metric_id"].isin(metric_ids)], metric_names)


def _latest_filtered_records(
    df: pd.DataFrame | None,
    metric_ids: set[str],
    metric_names: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    if df is None or df.empty or "metric_id" not in df:
        return []
    return _latest_metric_records(df[df["metric_id"].isin(metric_ids)], metric_names)


def _latest_records(
    df: pd.DataFrame | None,
    id_col: str,
    metric_names: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    if df is None or df.empty or id_col not in df or "date" not in df:
        return []
    data = df.copy()
    data["date"] = pd.to_datetime(data["date"])
    return _records(data.sort_values("date").groupby(id_col).tail(1), metric_names)


def _latest_metric_records(df: pd.DataFrame | None, metric_names: dict[str, str] | None = None) -> list[dict[str, Any]]:
    if df is None or df.empty or "metric_id" not in df or "date" not in df:
        return []
    data = df.copy()
    data["date"] = pd.to_datetime(data["date"])
    return _records(data.sort_values("date").groupby("metric_id").tail(1), metric_names)


def _rel_to(path: Path, parent: Path) -> str:
    try:
        return path.resolve().relative_to(parent.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _as_of_info(raw: pd.DataFrame, metrics: list[dict[str, Any]], as_of: str) -> dict[str, Any]:
    requested = pd.Timestamp.today().normalize() if as_of == "latest" else pd.to_datetime(as_of)
    generated_at = pd.Timestamp.now().isoformat(timespec="seconds")
    if raw.empty:
        return {
            "generated_at": generated_at,
            "requested_as_of": "latest" if as_of == "latest" else str(requested.date()),
            "latest_data_date_overall": "unavailable",
            "latest_data_date_by_asset_class": {},
        }
    data = raw.copy()
    data["date"] = pd.to_datetime(data["date"])
    data = data[data["date"] <= requested]
    metric_asset_classes = {m["metric_id"]: m.get("asset_class", "unknown") for m in metrics}
    data["asset_class"] = data["metric_id"].map(metric_asset_classes).fillna("unknown")
    by_asset = {
        asset_class: str(group["date"].max().date())
        for asset_class, group in data.groupby("asset_class")
        if not group.empty
    }
    overall = "unavailable" if data.empty else str(data["date"].max().date())
    return {
        "generated_at": generated_at,
        "requested_as_of": "latest" if as_of == "latest" else str(requested.date()),
        "latest_data_date_overall": overall,
        "latest_data_date_by_asset_class": by_asset,
    }


def _missing_metrics(raw: pd.DataFrame, metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    present = set() if raw.empty else set(raw["metric_id"].unique())
    return [m for m in metrics if m["metric_id"] not in present]


def _missing_summary(missing: list[dict[str, Any]], placeholders: list[dict[str, Any]], premium: list[dict[str, Any]]) -> str:
    return (
        f"{len(missing)} MVP series missing; "
        f"{len(placeholders)} placeholder datasets unavailable; "
        f"{len(premium)} premium-required datasets unavailable."
    )


def _key_moves(transforms: dict[str, pd.DataFrame], metric_names: dict[str, str]) -> list[str]:
    moves = []
    for name, label, column in [
        ("price_returns", "Equity", "1W_return_pct"),
        ("rate_changes", "Rates/credit", "1W_change_bps"),
        ("fx_returns", "FX", "1W_return_pct"),
    ]:
        df = transforms.get(name)
        if df is None or df.empty or column not in df:
            continue
        row = df.dropna(subset=[column]).sort_values(column, key=abs).tail(1)
        if not row.empty:
            item = row.iloc[0]
            unit = "%" if column.endswith("_pct") else " bps"
            moves.append(f"{label}: {metric_names.get(item['metric_id'], item['metric_id'])} {item[column]:.2f}{unit}")
    return moves


def _top_movers(transforms: dict[str, pd.DataFrame], metric_names: dict[str, str]) -> list[dict[str, Any]]:
    frames = []
    for df in [transforms.get("price_returns"), transforms.get("fx_returns")]:
        if df is not None and not df.empty and "1W_return_pct" in df:
            frames.append(df[["metric_id", "1W_return_pct"]].rename(columns={"1W_return_pct": "move"}))
    rates = transforms.get("rate_changes")
    if rates is not None and not rates.empty and "1W_change_bps" in rates:
        frames.append(rates[["metric_id", "1W_change_bps"]].rename(columns={"1W_change_bps": "move"}))
    if not frames:
        return []
    data = pd.concat(frames, ignore_index=True).dropna(subset=["move"])
    return _records(data.assign(abs_move=data["move"].abs()).sort_values("abs_move", ascending=False).head(5), metric_names)


def _metric_summary(metric: dict[str, Any]) -> dict[str, Any]:
    return {
        "metric_id": metric["metric_id"],
        "display_name": metric["display_name"],
        "premium_required": bool(metric.get("premium_required")),
        "notes": metric.get("notes", ""),
    }


def _validation_summary(path: Path) -> list[str]:
    if not path.exists():
        return ["Validation report unavailable."]
    lines = [line for line in path.read_text().splitlines() if line.startswith("- ")]
    return [line[2:] for line in lines]
