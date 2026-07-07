"""Markdown and JSON dashboard publishing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dashboard.config import ROOT


DASHBOARD_MD = ROOT / "output" / "dashboard.md"
DASHBOARD_JSON = ROOT / "output" / "dashboard.json"


def write_dashboard(layout: dict[str, Any], md_path: Path = DASHBOARD_MD, json_path: Path = DASHBOARD_JSON) -> tuple[Path, Path]:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(layout))
    json_path.write_text(json.dumps(layout, indent=2, default=str) + "\n")
    return md_path, json_path


def render_markdown(layout: dict[str, Any]) -> str:
    sections = layout["sections"]
    snapshot = layout["executive_snapshot"]
    lines = [
        "# Weekly Financial Dashboard",
        "",
        "## Executive Snapshot",
        f"- Generated at: {snapshot['generated_at']}",
        f"- Requested as-of: {snapshot['requested_as_of']}",
        f"- Latest data date overall: {snapshot['data_as_of_date']}",
        f"- Latest data date by asset class: {_inline_dict(snapshot['latest_data_date_by_asset_class'])}",
        f"- Missing-data summary: {snapshot['missing_data_summary']}",
        "",
        "### Key Cross-Asset Moves",
        *_bullets(snapshot["key_cross_asset_moves"]),
        "",
        "### Top Movers",
        _table(snapshot["top_movers"]),
        "",
        "## Equity",
        "### Global Index Return Table",
        _table(sections["equity"]["global_index_return_table"]),
        _image(sections["equity"]["chart"], "Equity indices normalized"),
        _image(sections["equity"]["global_equity_indices_chart"], "Global equity indices normalized"),
        _image(sections["equity"]["global_equity_indices_heatmap"], "Global equity index return heatmap"),
        _image(sections["equity"]["factor_proxy_ratios_chart"], "Factor proxy ratios"),
        "### Factor Proxies",
        _table(sections["equity"]["factor_proxy_table"]),
        _image(sections["equity"]["us_sector_heatmap"], "US sector ETF heatmap"),
        "### US Sector ETF Returns",
        _table(sections["equity"]["us_sector_table"]),
        f"- Growth vs Value: {sections['equity']['growth_vs_value']}",
        f"- Cyclicals vs Defensives: {sections['equity']['cyclicals_vs_defensives']}",
        f"- Sector heatmap: {sections['equity']['sector_heatmap']}",
        "",
        "## Rates",
        f"- Curve display: {sections['rates']['us_treasury_curve_note']}",
        _image(sections["rates"]["us_treasury_curve_chart"], "US Treasury curve"),
        _image(sections["rates"]["us_curve_spreads_chart"], "US curve spreads"),
        _image(sections["rates"]["us_curve_spreads_expanded_chart"], "Expanded US curve spreads"),
        _image(sections["rates"]["fed_corridor_chart"], "Fed corridor"),
        _image(sections["rates"]["us_money_market_corridor_chart"], "US money market corridor"),
        _image(sections["rates"]["us_liquidity_stack_chart"], "US liquidity stack"),
        "### US Curve Spreads",
        _table(sections["rates"]["curve_spreads"]),
        "### US Rate Spreads",
        _table(sections["rates"]["us_rate_spreads"]),
        "### Money Market Indicators",
        _table(sections["rates"]["money_market_indicators"]),
        "",
        "## EU Rates",
        f"- Curve display: {sections['eu_rates']['eu_yield_curve_note']}",
        _image(sections["eu_rates"]["eu_yield_curve_chart"], "EUR yield curve"),
        _image(sections["eu_rates"]["ecb_policy_rates_chart"], "ECB policy rates"),
        "### ECB Policy / Overnight Rates",
        _table(sections["eu_rates"]["policy_rates"]),
        "### EUR Curve Key Tenors",
        _table(sections["eu_rates"]["curve_tenors"]),
        "",
        "## Treasury Auctions",
        _image(sections["treasury_auctions"]["bid_to_cover_chart"], "Treasury auction bid-to-cover"),
        _image(sections["treasury_auctions"]["allocation_chart"], "Treasury auction allocation"),
        _image(sections["treasury_auctions"]["net_issuance_chart"], "Treasury net issuance proxy"),
        "### Recent Auction Calendar",
        _table(sections["treasury_auctions"]["auction_calendar_table"]),
        "### Latest Auction Metrics",
        _table(sections["treasury_auctions"]["auction_metrics"]),
        f"- Tail / stop-through: {sections['treasury_auctions']['tail_stop_note']}",
        "",
        "## HK Rates",
        f"- Curve display: {sections['hk_rates']['hibor_curve_note']}",
        _image(sections["hk_rates"]["hibor_curve_chart"], "HK HIBOR curve"),
        _image(sections["hk_rates"]["hkma_aggregate_balance_chart"], "HKMA aggregate balance"),
        _image(sections["hk_rates"]["hibor_sofr_spreads_chart"], "HIBOR-SOFR proxy spreads"),
        "### Latest HIBOR Tenors",
        _table(sections["hk_rates"]["latest_hibor_tenors"]),
        "### HIBOR-SOFR Proxy Spreads",
        _table(sections["hk_rates"]["hibor_sofr_spreads"]),
        f"- Note: {sections['hk_rates']['notes']}",
        "",
        "## Asia Rates",
        f"- Japan curve display: {sections['asia_rates']['jp_jgb_curve_note']}",
        _image(sections["asia_rates"]["jp_jgb_curve_chart"], "Japan JGB curve"),
        _image(sections["asia_rates"]["jp_jgb_yields_chart"], "Japan JGB key yields"),
        "### Japan JGB Key Yields",
        _table(sections["asia_rates"]["jp_key_yields"]),
        "",
        "## China Rates",
        f"- Manual fallback: {sections['china_rates']['manual_csv_note']}",
        _image(sections["china_rates"]["cn_cgb_curve_chart"], "China CGB curve"),
        _image(sections["china_rates"]["cn_money_market_rates_chart"], "China money market rates"),
        _image(sections["china_rates"]["cn_policy_rates_chart"], "China policy rates"),
        "### China CGB Key Yields",
        _table(sections["china_rates"]["cgb_key_yields"]),
        "### China Money Market Rates",
        _table(sections["china_rates"]["money_market_rates"]),
        "### China Policy Rates",
        _table(sections["china_rates"]["policy_rates"]),
        "",
        "## Credit",
        _image(sections["credit"]["us_ig_hy_spread_chart"], "US IG/HY spread chart"),
        _table(sections["credit"]["spread_table"]),
        _image(sections["credit"]["eu_credit_spreads_chart"], "EU credit spreads"),
        _table(sections["credit"]["eu_spread_table"]),
        "",
        "## FX",
        "### FX Spot Table",
        _table(sections["fx"]["fx_spot_table"]),
        _image(sections["fx"]["fx_spot_heatmap"], "FX spot heatmap"),
        _image(sections["fx"]["fx_spot_expanded_heatmap"], "Expanded FX spot heatmap"),
        f"- FX implied vol: {sections['fx']['fx_implied_vol']}",
        f"- Cross-currency basis: {sections['fx']['cross_currency_basis']}",
        "",
        "## Cross-Market",
        f"- Yield differentials: {sections['cross_market']['yield_differentials_note']}",
        _image(sections["cross_market"]["yield_differentials_heatmap"], "Cross-market yield differentials heatmap"),
        "### Cross-Market Yield Differentials",
        _table(sections["cross_market"]["yield_differentials_table"]),
        "",
        "## Missing / Premium-Required Data",
        "### Unavailable Datasets",
        _table(sections["missing_premium_required_data"]["unavailable_datasets"]),
        "### Premium-Required Datasets",
        _table(sections["missing_premium_required_data"]["premium_required_datasets"]),
        "",
        "## Source Validation Summary",
        *_bullets(sections["source_validation_summary"]),
        "",
    ]
    return "\n".join(lines)


def _bullets(items: list[Any]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- None"]


def _image(path: str | None, alt: str) -> str:
    return f"![{alt}]({path})" if path else f"_{alt} unavailable._"


def _table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No data available._"
    columns = list(rows[0].keys())
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = ["| " + " | ".join(_format(row.get(col)) for col in columns) + " |" for row in rows]
    return "\n".join([header, divider, *body])


def _format(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value).replace("\n", " ")


def _inline_dict(value: dict[str, Any]) -> str:
    if not value:
        return "unavailable"
    return ", ".join(f"{key}: {item}" for key, item in sorted(value.items()))
