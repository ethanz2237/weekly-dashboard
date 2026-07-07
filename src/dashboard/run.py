"""CLI for the weekly financial dashboard."""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path

import pandas as pd

from dashboard.charts.matplotlib_charts import generate_dashboard_charts
from dashboard.config import load_dotenv, load_metrics_catalog, mvp_metrics
from dashboard.fetchers import china_fetcher, ecb_fetcher, fred_fetcher, hkma_fetcher, mof_fetcher, openbb_fetcher, treasury_fetcher, yfinance_fetcher
from dashboard.publish.layout import build_dashboard_layout
from dashboard.publish.markdown import write_dashboard
from dashboard.publish.notion import publish_dashboard
from dashboard.transforms.fx import calculate_fx_returns
from dashboard.transforms.rates import (
    calculate_bps_changes,
    calculate_cross_market_yield_differentials,
    calculate_curve_spreads,
    calculate_hibor_sofr_spreads,
    calculate_us_rate_spreads,
)
from dashboard.transforms.returns import calculate_price_returns
from dashboard.utils.cache import save_processed, save_raw
from dashboard.utils.cache import cache_available
from dashboard.utils.http import get_json, get_text
from dashboard.utils.sanitize import sanitize
from dashboard.utils.validation import missing_credentials, write_report


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
VALID_MODES = ("build", "validate-sources", "publish-notion", "check-env", "source-health", "pre-notion-check")
EQUITY_INDEX_IDS = {
    "sp500",
    "nasdaq100",
    "csi300",
    "chinext",
    "hsi",
    "hstech",
    "stoxx50",
    "stoxx600",
    "nikkei225",
    "topix",
    "kospi",
    "twse",
    "nifty50",
    "idx",
}
FX_SPOT_IDS = {"eurusd", "usdjpy", "usdhkd", "usdkrw", "usdtwd", "usdcny", "cnycnh", "usdidr", "usdinr"}
SECTOR_ETF_IDS = {"xlp", "xlu", "xlv", "xly", "xli", "xlf", "xlk", "xle", "xlb", "xlre", "xlc"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Weekly financial dashboard runner.")
    parser.add_argument("--as-of", default="latest", help="As-of date, or 'latest'.")
    parser.add_argument("--mode", choices=VALID_MODES, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_dotenv(ENV_PATH)

    if args.mode == "check-env":
        check_env()
        return
    if args.mode == "source-health":
        source_health()
        return

    all_metrics = load_metrics_catalog()
    metrics = mvp_metrics(all_metrics)

    if args.mode == "publish-notion":
        result = publish_dashboard(args.as_of)
        print(result.message + (f" Page: {result.url or result.page_id}" if result.success and (result.url or result.page_id) else ""))
        return

    raw, issues = fetch_mvp_data(metrics, args.as_of)
    for name in missing_credentials(metrics, os.environ):
        if not any(name in issue for issue in issues):
            issues.append(f"Missing credential: {name}")
    save_raw(raw, "mvp_market_data")
    outputs = run_transforms(raw, args.as_of)
    validation_data = validation_frame(raw, outputs)
    report = write_report(validation_data, all_metrics, issues)
    coverage_report = write_report(validation_data, all_metrics, issues, PROJECT_ROOT / "output" / "data_coverage_report.md")

    if args.mode == "validate-sources":
        print(f"Validation report written to {report}")
        return

    chart_paths = generate_dashboard_charts(
        raw,
        outputs["curve_spreads"],
        outputs["fx_returns"],
        outputs["hibor_sofr_spreads"],
        outputs.get("price_returns"),
        outputs.get("factor_proxy_ratios"),
        outputs.get("sector_returns"),
        outputs.get("us_rate_spreads"),
        outputs.get("treasury_auction_calendar_table"),
        outputs.get("cross_market_yield_differentials"),
    )
    md_path_hint = PROJECT_ROOT / "output" / "dashboard.md"
    layout = build_dashboard_layout(
        raw,
        outputs,
        all_metrics,
        metrics,
        chart_paths,
        report,
        args.as_of,
        markdown_parent=md_path_hint.parent,
    )
    md_path, json_path = write_dashboard(layout, md_path=md_path_hint)
    print(
        f"Build complete. Charts: {len(chart_paths)}. "
        f"Dashboard: {md_path}, {json_path}. Validation report: {report}. Coverage report: {coverage_report}"
    )


def fetch_mvp_data(metrics: list[dict], as_of: str) -> tuple[pd.DataFrame, list[str]]:
    frames: list[pd.DataFrame] = []
    issues: list[str] = []
    for fetcher in (openbb_fetcher, fred_fetcher, yfinance_fetcher, ecb_fetcher, mof_fetcher, china_fetcher, hkma_fetcher, treasury_fetcher):
        frame, fetch_issues = fetcher.fetch(metrics, as_of)
        issues.extend(fetch_issues)
        if not frame.empty:
            frames.append(frame)
    if not frames:
        return _empty_normalized(), issues
    data = pd.concat(frames, ignore_index=True)
    data["date"] = pd.to_datetime(data["date"]).dt.date
    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    return data.dropna(subset=["value"]).sort_values(["metric_id", "date"]), issues


def run_transforms(raw: pd.DataFrame, as_of: str) -> dict[str, pd.DataFrame]:
    price_like = raw[raw["metric_id"].isin(EQUITY_INDEX_IDS)] if not raw.empty else raw
    sector_like = raw[raw["metric_id"].isin(SECTOR_ETF_IDS)] if not raw.empty else raw
    rates_like = raw[
        raw["metric_id"].isin(
            [
                "us_2y_yield",
                "us_1m_yield",
                "us_3m_yield",
                "us_6m_yield",
                "us_1y_yield",
                "us_3y_yield",
                "us_5y_yield",
                "us_7y_yield",
                "us_10y_yield",
                "us_20y_yield",
                "us_30y_yield",
                "eur_on_rate",
                "eur_3m_yield",
                "eur_6m_yield",
                "eur_1y_yield",
                "eur_2y_yield",
                "eur_3y_yield",
                "eur_5y_yield",
                "eur_7y_yield",
                "eur_10y_yield",
                "eur_20y_yield",
                "eur_30y_yield",
                "ecb_deposit_rate",
                "ecb_main_refi_rate",
                "ecb_marginal_lending_rate",
                "jgb_1y",
                "jgb_2y",
                "jgb_3y",
                "jgb_4y",
                "jgb_5y",
                "jgb_6y",
                "jgb_7y",
                "jgb_8y",
                "jgb_9y",
                "jgb_10y",
                "jgb_15y",
                "jgb_20y",
                "jgb_25y",
                "jgb_30y",
                "jgb_40y",
                "cgb_2y",
                "cgb_5y",
                "cgb_10y",
                "cgb_30y",
                "dr007",
                "fr007",
                "lpr",
                "mlf",
                "slf",
                "sofr",
                "effr",
                "iorb",
                "us_3m_tbill_yield",
                "on_rrp_rate",
                "on_rrp_usage",
                "obfr",
                "tga",
                "srf_usage",
                "bank_reserves",
                "us_hy_oas",
                "us_ig_oas",
                "eu_hy_oas",
            ]
        )
    ] if not raw.empty else raw
    us_spread_input = raw[
        raw["metric_id"].isin(["sofr", "effr", "iorb"])
    ] if not raw.empty else raw
    hk_rates_like = raw[
        raw["metric_id"].isin(
            [
                "hibor_on",
                "hibor_1w",
                "hibor_1m",
                "hibor_3m",
                "hibor_6m",
                "hibor_12m",
                "hkma_aggregate_balance",
            ]
        )
    ] if not raw.empty else raw
    spread_input = raw[
        raw["metric_id"].isin(["sofr", "hibor_on", "hibor_1m", "hibor_3m", "hibor_6m"])
    ] if not raw.empty else raw
    fx_like = raw[raw["metric_id"].isin(FX_SPOT_IDS)] if not raw.empty else raw
    cross_market_input = raw[
        raw["metric_id"].isin(
            [
                "eur_3m_yield",
                "eur_2y_yield",
                "eur_10y_yield",
                "jgb_2y",
                "jgb_10y",
                "us_3m_tbill_yield",
                "us_2y_yield",
                "us_10y_yield",
            ]
        )
    ] if not raw.empty else raw

    outputs = {
        "price_returns": calculate_price_returns(price_like, as_of),
        "sector_returns": calculate_price_returns(sector_like, as_of),
        "factor_proxy_ratios": calculate_factor_proxy_ratios(raw, as_of),
        "rate_changes": calculate_bps_changes(rates_like, as_of),
        "hk_rate_changes": calculate_bps_changes(hk_rates_like, as_of),
        "curve_spreads": calculate_curve_spreads(rates_like, as_of),
        "us_rate_spreads": calculate_us_rate_spreads(us_spread_input, as_of),
        "hibor_sofr_spreads": calculate_hibor_sofr_spreads(spread_input, as_of),
        "cross_market_yield_differentials": calculate_cross_market_yield_differentials(cross_market_input, as_of),
        "fx_returns": calculate_fx_returns(fx_like, as_of),
        "treasury_auction_calendar_table": treasury_auction_calendar(raw),
    }
    for name, frame in outputs.items():
        save_processed(frame, name)
    return outputs


def validation_frame(raw: pd.DataFrame, outputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    frames = [raw]
    factors = outputs.get("factor_proxy_ratios")
    if factors is not None and not factors.empty:
        validation_factors = factors[["date", "metric_id", "value"]].copy()
        validation_factors["source"] = "computed"
        validation_factors["provider"] = "internal"
        validation_factors["as_of_date"] = pd.Timestamp.today().date().isoformat()
        frames.append(validation_factors)
    sectors = outputs.get("sector_returns")
    if sectors is not None and not sectors.empty:
        validation_sectors = pd.DataFrame(
            [
                {
                    "date": sectors["latest_date"].max(),
                    "metric_id": "us_sector_etf_heatmap",
                    "value": sectors["1W_return_pct"].dropna().mean(),
                    "source": "computed",
                    "provider": "internal",
                    "as_of_date": pd.Timestamp.today().date().isoformat(),
                }
            ]
        )
        frames.append(validation_sectors)
    spreads = outputs.get("hibor_sofr_spreads")
    if spreads is not None and not spreads.empty:
        validation_spreads = spreads.copy()
        validation_spreads["source"] = "computed"
        validation_spreads["provider"] = "internal"
        validation_spreads["as_of_date"] = pd.Timestamp.today().date().isoformat()
        frames.append(validation_spreads[["date", "metric_id", "value", "source", "provider", "as_of_date"]])
    us_rate_spreads = outputs.get("us_rate_spreads")
    if us_rate_spreads is not None and not us_rate_spreads.empty:
        validation_us_rate_spreads = us_rate_spreads.copy()
        validation_us_rate_spreads["source"] = "computed"
        validation_us_rate_spreads["provider"] = "internal"
        validation_us_rate_spreads["as_of_date"] = pd.Timestamp.today().date().isoformat()
        frames.append(
            validation_us_rate_spreads[["date", "metric_id", "value", "source", "provider", "as_of_date"]]
        )
    curve_spreads = outputs.get("curve_spreads")
    if curve_spreads is not None and not curve_spreads.empty and "metric_id" in curve_spreads:
        validation_curve_spreads = curve_spreads.copy()
        validation_curve_spreads["source"] = "computed"
        validation_curve_spreads["provider"] = "internal"
        validation_curve_spreads["as_of_date"] = pd.Timestamp.today().date().isoformat()
        frames.append(
            validation_curve_spreads[["date", "metric_id", "value", "source", "provider", "as_of_date"]]
        )
    cross_market = outputs.get("cross_market_yield_differentials")
    if cross_market is not None and not cross_market.empty:
        validation_cross_market = cross_market.copy()
        validation_cross_market["source"] = "computed"
        validation_cross_market["provider"] = "internal"
        validation_cross_market["as_of_date"] = pd.Timestamp.today().date().isoformat()
        frames.append(validation_cross_market[["date", "metric_id", "value", "source", "provider", "as_of_date"]])
    return pd.concat([frame for frame in frames if not frame.empty], ignore_index=True) if frames else _empty_normalized()


def _empty_normalized() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "metric_id", "value", "source", "provider", "as_of_date"])


def calculate_factor_proxy_ratios(raw: pd.DataFrame, as_of: str) -> pd.DataFrame:
    data = raw.copy()
    if data.empty:
        return pd.DataFrame(columns=["date", "metric_id", "value"])
    data["date"] = pd.to_datetime(data["date"])
    if as_of != "latest":
        data = data[data["date"] <= pd.to_datetime(as_of)]
    wide = data.pivot_table(index="date", columns="metric_id", values="value", aggfunc="last").sort_index()
    rows = []
    if {"iwf", "iwd"} <= set(wide.columns):
        rows.append((wide["iwf"] / wide["iwd"] * 100).rename("growth_vs_value_proxy"))
    defensives = [col for col in ["xlp", "xlu", "xlv"] if col in wide]
    cyclicals = [col for col in ["xly", "xli", "xlf"] if col in wide]
    if defensives and cyclicals:
        rows.append((wide[defensives].mean(axis=1) / wide[cyclicals].mean(axis=1) * 100).rename("defensives_vs_cyclicals_proxy"))
    if not rows:
        return pd.DataFrame(columns=["date", "metric_id", "value"])
    result = pd.concat(rows, axis=1).reset_index().melt(id_vars="date", var_name="metric_id", value_name="value")
    return result.dropna(subset=["value"])


def treasury_auction_calendar(raw: pd.DataFrame, limit: int = 20) -> pd.DataFrame:
    if raw.empty or "metric_id" not in raw:
        return pd.DataFrame()
    data = raw[raw["metric_id"] == "treasury_auction_bid_to_cover"].copy()
    required = {"date", "security_type", "security_term", "cusip", "value", "offering_amt", "total_accepted"}
    if data.empty or not required <= set(data.columns):
        return pd.DataFrame()
    data["date"] = pd.to_datetime(data["date"])
    data = data.sort_values("date", ascending=False).head(limit)
    return data.rename(columns={"value": "bid_to_cover"})[
        ["date", "security_type", "security_term", "cusip", "offering_amt", "total_accepted", "bid_to_cover"]
    ]


def check_env() -> None:
    fred_key = os.getenv("FRED_API_KEY", "")
    notion_token = os.getenv("NOTION_TOKEN", "")
    notion_database_id = os.getenv("NOTION_DATABASE_ID", "")
    notion_data_source_id = os.getenv("NOTION_DATA_SOURCE_ID", "")
    print(f".env found: {ENV_PATH.exists()} ({ENV_PATH})")
    print(f"FRED_API_KEY: {_mask(fred_key) if fred_key else 'missing'}")
    print(f"NOTION_TOKEN: {_mask(notion_token) if notion_token else 'missing'}")
    print(f"NOTION_DATABASE_ID: {_mask(notion_database_id) if notion_database_id else 'missing'}")
    print(f"NOTION_DATA_SOURCE_ID: {_mask(notion_data_source_id) if notion_data_source_id else 'missing'}")
    print(f"yfinance imports: {_imports('yfinance')}")
    print(f"OpenBB imports: {_imports('openbb')}")


def source_health() -> None:
    checks = [
        ("FRED DGS10", fred_fetcher.FRED_OBSERVATIONS_URL, {"series_id": "DGS10", "api_key": os.getenv("FRED_API_KEY", ""), "file_type": "json", "observation_start": "2026-01-01"}, ["us_10y_yield"]),
        ("HKMA HIBOR fixing", hkma_fetcher.HIBOR_URL, {"segment": "hibor.fixing", "offset": 0}, ["hibor_on", "hibor_1m", "hibor_3m"]),
        ("HKMA Aggregate Balance", hkma_fetcher.MONETARY_BASE_URL, {"offset": 0}, ["hkma_aggregate_balance"]),
        ("Treasury FiscalData", treasury_fetcher.AUCTIONS_URL, {"page[size]": 1, "sort": "-auction_date"}, ["treasury_auction_bid_to_cover"]),
    ]
    for name, url, params, metric_ids in checks:
        try:
            get_json(url, params=params, timeout=30, retries=1)
            status, error = "OK", ""
        except Exception as exc:
            status, error = "failed", sanitize(exc)
        cache = cache_available(metric_ids, 60)
        print(f"{name}: {status}; cache_available={cache}" + (f"; error={error}" if error else ""))
    for name, url, metric_ids in [
        ("ECB EUR 10Y", f"{ecb_fetcher.ECB_DATA_URL}/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y", ["eur_10y_yield"]),
        ("Japan MOF JGB", mof_fetcher.JGB_RATES_URL, ["jgb_10y"]),
    ]:
        try:
            get_text(url, params={"startPeriod": "2026-01-01", "format": "csvdata"} if "ECB" in name else None, timeout=30, retries=1)
            status, error = "OK", ""
        except Exception as exc:
            status, error = "failed", sanitize(exc)
        cache = cache_available(metric_ids, 60)
        print(f"{name}: {status}; cache_available={cache}" + (f"; error={error}" if error else ""))


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def _imports(module_name: str) -> bool:
    try:
        if importlib.util.find_spec(module_name) is None:
            return False
        __import__(module_name)
    except Exception:
        return False
    return True


if __name__ == "__main__":
    main()
