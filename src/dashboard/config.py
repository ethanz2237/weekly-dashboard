"""Configuration loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
METRICS_CATALOG = ROOT / "config" / "metrics_catalog.yml"
MVP_METRIC_IDS = {
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
    "growth_vs_value_proxy",
    "defensives_vs_cyclicals_proxy",
    "us_sector_etf_heatmap",
    "iwf",
    "iwd",
    "xlp",
    "xlu",
    "xlv",
    "xly",
    "xli",
    "xlf",
    "xlk",
    "xle",
    "xlb",
    "xlre",
    "xlc",
    "us_1m_yield",
    "us_3m_yield",
    "us_6m_yield",
    "us_1y_yield",
    "us_2y_yield",
    "us_3y_yield",
    "us_5y_yield",
    "us_7y_yield",
    "us_10y_yield",
    "us_20y_yield",
    "us_30y_yield",
    "us_2s10s",
    "us_5s30s",
    "us_10s30s",
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
    "us_3m_tbill_yield",
    "sofr",
    "effr",
    "iorb",
    "on_rrp_rate",
    "on_rrp_usage",
    "obfr",
    "sofr_minus_effr",
    "iorb_minus_effr",
    "tga",
    "srf_usage",
    "bank_reserves",
    "treasury_auction_net_issuance",
    "treasury_auction_bid_to_cover",
    "treasury_auction_direct_bidders",
    "treasury_auction_indirect_bidders",
    "treasury_auction_primary_dealer_allocation",
    "us_hy_oas",
    "us_ig_oas",
    "eu_hy_oas",
    "eurusd",
    "usdjpy",
    "usdhkd",
    "usdkrw",
    "usdtwd",
    "usdcny",
    "cnycnh",
    "usdidr",
    "usdinr",
    "hibor_on",
    "hibor_1w",
    "hibor_1m",
    "hibor_3m",
    "hibor_6m",
    "hibor_12m",
    "hkma_aggregate_balance",
    "hibor_on_minus_sofr",
    "hibor_1m_minus_sofr",
    "hibor_3m_minus_sofr",
    "hibor_6m_minus_sofr",
    "eurusd_3m_yield_diff",
    "eurusd_2y_yield_diff",
    "eurusd_10y_yield_diff",
    "usdjpy_2y_yield_diff",
    "usdjpy_10y_yield_diff",
}


def load_metrics_catalog(path: Path = METRICS_CATALOG) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text()) or {}
    return data.get("metrics", [])


def mvp_metrics(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [metric for metric in metrics if metric["metric_id"] in MVP_METRIC_IDS]


def load_dotenv(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    import os

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
