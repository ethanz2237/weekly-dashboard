"""Matplotlib chart helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from dashboard.charts.formatting import format_value, infer_format
from dashboard.config import ROOT


CHART_DIR = ROOT / "output" / "charts"


def line_chart(
    df: pd.DataFrame,
    path: Path,
    title: str,
    id_col: str = "metric_id",
    annotate_latest: bool = True,
    value_format: str | None = None,
) -> Path:
    fig, ax = plt.subplots(figsize=(9, 5))
    data = _prep(df)
    if data.empty:
        _empty(ax, title)
    else:
        plotted = []
        for metric_id, group in data.groupby(id_col):
            group = group.sort_values("date")
            (line,) = ax.plot(group["date"], group["value"], label=str(metric_id), linewidth=1.8)
            plotted.append((line, group))
        ax.set_title(title)
        ax.legend(loc="best")
        ax.grid(True, alpha=0.25)
        if annotate_latest:
            _annotate_latest_lines(ax, plotted, value_format or infer_format(title))
    return _save(fig, path)


def normalized_line_chart(df: pd.DataFrame, path: Path, title: str, annotate_latest: bool = True) -> Path:
    fig, ax = plt.subplots(figsize=(9, 5))
    data = _prep(df)
    if data.empty:
        _empty(ax, title)
    else:
        plotted = []
        for metric_id, group in data.groupby("metric_id"):
            group = group.sort_values("date")
            first = group["value"].iloc[0]
            if first == 0:
                continue
            plot_group = group.assign(value=group["value"] / first * 100)
            (line,) = ax.plot(plot_group["date"], plot_group["value"], label=str(metric_id), linewidth=1.8)
            plotted.append((line, plot_group))
        ax.set_title(title)
        ax.set_ylabel("Start = 100")
        ax.legend(loc="best")
        ax.grid(True, alpha=0.25)
        if annotate_latest:
            _annotate_latest_lines(ax, plotted, "integer")
    return _save(fig, path)


UST_TENORS = [
    {"metric_id": "us_1m_yield", "tenor": "1M", "tenor_order": 1, "highlight": False},
    {"metric_id": "us_3m_yield", "tenor": "3M", "tenor_order": 2, "highlight": False},
    {"metric_id": "us_6m_yield", "tenor": "6M", "tenor_order": 3, "highlight": False},
    {"metric_id": "us_1y_yield", "tenor": "1Y", "tenor_order": 4, "highlight": False},
    {"metric_id": "us_2y_yield", "tenor": "2Y", "tenor_order": 5, "highlight": True},
    {"metric_id": "us_3y_yield", "tenor": "3Y", "tenor_order": 6, "highlight": False},
    {"metric_id": "us_5y_yield", "tenor": "5Y", "tenor_order": 7, "highlight": True},
    {"metric_id": "us_7y_yield", "tenor": "7Y", "tenor_order": 8, "highlight": False},
    {"metric_id": "us_10y_yield", "tenor": "10Y", "tenor_order": 9, "highlight": True},
    {"metric_id": "us_20y_yield", "tenor": "20Y", "tenor_order": 10, "highlight": False},
    {"metric_id": "us_30y_yield", "tenor": "30Y", "tenor_order": 11, "highlight": True},
]

HIBOR_TENORS = [
    {"metric_id": "hibor_on", "tenor": "O/N", "tenor_order": 1, "highlight": True},
    {"metric_id": "hibor_1w", "tenor": "1W", "tenor_order": 2, "highlight": False},
    {"metric_id": "hibor_1m", "tenor": "1M", "tenor_order": 3, "highlight": True},
    {"metric_id": "hibor_3m", "tenor": "3M", "tenor_order": 4, "highlight": True},
    {"metric_id": "hibor_6m", "tenor": "6M", "tenor_order": 5, "highlight": True},
    {"metric_id": "hibor_12m", "tenor": "12M", "tenor_order": 6, "highlight": False},
]

EUR_TENORS = [
    {"metric_id": "eur_3m_yield", "tenor": "3M", "tenor_order": 1, "highlight": False},
    {"metric_id": "eur_6m_yield", "tenor": "6M", "tenor_order": 2, "highlight": False},
    {"metric_id": "eur_1y_yield", "tenor": "1Y", "tenor_order": 3, "highlight": False},
    {"metric_id": "eur_2y_yield", "tenor": "2Y", "tenor_order": 4, "highlight": True},
    {"metric_id": "eur_3y_yield", "tenor": "3Y", "tenor_order": 5, "highlight": False},
    {"metric_id": "eur_5y_yield", "tenor": "5Y", "tenor_order": 6, "highlight": True},
    {"metric_id": "eur_7y_yield", "tenor": "7Y", "tenor_order": 7, "highlight": False},
    {"metric_id": "eur_10y_yield", "tenor": "10Y", "tenor_order": 8, "highlight": True},
    {"metric_id": "eur_20y_yield", "tenor": "20Y", "tenor_order": 9, "highlight": False},
    {"metric_id": "eur_30y_yield", "tenor": "30Y", "tenor_order": 10, "highlight": True},
]

JGB_TENORS = [
    {"metric_id": "jgb_1y", "tenor": "1Y", "tenor_order": 1, "highlight": False},
    {"metric_id": "jgb_2y", "tenor": "2Y", "tenor_order": 2, "highlight": True},
    {"metric_id": "jgb_3y", "tenor": "3Y", "tenor_order": 3, "highlight": False},
    {"metric_id": "jgb_4y", "tenor": "4Y", "tenor_order": 4, "highlight": False},
    {"metric_id": "jgb_5y", "tenor": "5Y", "tenor_order": 5, "highlight": True},
    {"metric_id": "jgb_6y", "tenor": "6Y", "tenor_order": 6, "highlight": False},
    {"metric_id": "jgb_7y", "tenor": "7Y", "tenor_order": 7, "highlight": False},
    {"metric_id": "jgb_8y", "tenor": "8Y", "tenor_order": 8, "highlight": False},
    {"metric_id": "jgb_9y", "tenor": "9Y", "tenor_order": 9, "highlight": False},
    {"metric_id": "jgb_10y", "tenor": "10Y", "tenor_order": 10, "highlight": True},
    {"metric_id": "jgb_15y", "tenor": "15Y", "tenor_order": 11, "highlight": False},
    {"metric_id": "jgb_20y", "tenor": "20Y", "tenor_order": 12, "highlight": False},
    {"metric_id": "jgb_25y", "tenor": "25Y", "tenor_order": 13, "highlight": False},
    {"metric_id": "jgb_30y", "tenor": "30Y", "tenor_order": 14, "highlight": True},
    {"metric_id": "jgb_40y", "tenor": "40Y", "tenor_order": 15, "highlight": False},
]

CGB_TENORS = [
    {"metric_id": "cgb_2y", "tenor": "2Y", "tenor_order": 1, "highlight": True},
    {"metric_id": "cgb_5y", "tenor": "5Y", "tenor_order": 2, "highlight": True},
    {"metric_id": "cgb_10y", "tenor": "10Y", "tenor_order": 3, "highlight": True},
    {"metric_id": "cgb_30y", "tenor": "30Y", "tenor_order": 4, "highlight": True},
]


def curve_chart(
    df: pd.DataFrame,
    path: Path,
    title: str,
    tenors: list[dict[str, Any]] | None = None,
    ylabel: str = "Percent",
    value_format: str = "percent",
    annotate_latest: bool = True,
) -> Path:
    return snapshot_curve_chart(
        df,
        path,
        title,
        tenors or UST_TENORS,
        ylabel=ylabel,
        value_format=value_format,
        annotate_latest=annotate_latest,
    )


def snapshot_curve_chart(
    df: pd.DataFrame,
    path: Path,
    title: str,
    tenors: list[dict[str, Any]],
    ylabel: str = "Percent",
    value_format: str = "percent",
    annotate_latest: bool = True,
) -> Path:
    data = _prep(df)
    fig, ax = plt.subplots(figsize=(8, 5))
    ordered = sorted(tenors, key=lambda item: item.get("tenor_order", 999))
    metric_ids = [item["metric_id"] for item in ordered]
    labels = [item["tenor"] for item in ordered]
    if data.empty:
        _empty(ax, title)
        return _save(fig, path)
    wide = data[data["metric_id"].isin(metric_ids)].pivot_table(
        index="date", columns="metric_id", values="value", aggfunc="last"
    ).sort_index()
    if wide.empty:
        _empty(ax, title)
        return _save(fig, path)
    latest_date = wide.index.max()
    anchors = [("Latest", latest_date), ("1W Ago", latest_date - pd.Timedelta(days=7)), ("1M Ago", latest_date - pd.Timedelta(days=30))]
    plotted = False
    latest_values: list[Any] = []
    for label, target in anchors:
        subset = wide[wide.index <= target]
        if subset.empty:
            continue
        row = subset.iloc[-1]
        values = [row.get(metric_id) for metric_id in metric_ids]
        if any(pd.notna(value) for value in values):
            ax.plot(labels, values, marker="o", linewidth=2, label=label)
            if label == "Latest":
                latest_values = values
            plotted = True
    if not plotted:
        _empty(ax, title)
    else:
        if annotate_latest and latest_values:
            highlight_indexes = [idx for idx, item in enumerate(ordered) if item.get("highlight")]
            if len(labels) <= 6 and len(highlight_indexes) < len(labels):
                highlight_indexes = list(range(len(labels)))
            _annotate_points(ax, labels, latest_values, value_format, indexes=highlight_indexes)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.25)
        ax.legend(loc="best")
    return _save(fig, path)


def hk_hibor_curve_chart(df: pd.DataFrame, path: Path, annotate_latest: bool = True) -> Path:
    return snapshot_curve_chart(
        df,
        path,
        "HK HIBOR Curve",
        HIBOR_TENORS,
        ylabel="Percent",
        value_format="percent",
        annotate_latest=annotate_latest,
    )


def eu_yield_curve_chart(df: pd.DataFrame, path: Path, annotate_latest: bool = True) -> Path:
    return snapshot_curve_chart(
        df,
        path,
        "EUR Yield Curve",
        EUR_TENORS,
        ylabel="Percent",
        value_format="percent",
        annotate_latest=annotate_latest,
    )


def jp_jgb_curve_chart(df: pd.DataFrame, path: Path, annotate_latest: bool = True) -> Path:
    return snapshot_curve_chart(
        df,
        path,
        "Japan JGB Curve",
        JGB_TENORS,
        ylabel="Percent",
        value_format="percent",
        annotate_latest=annotate_latest,
    )


def cn_cgb_curve_chart(df: pd.DataFrame, path: Path, annotate_latest: bool = True) -> Path:
    return snapshot_curve_chart(
        df,
        path,
        "China CGB Curve",
        CGB_TENORS,
        ylabel="Percent",
        value_format="percent",
        annotate_latest=annotate_latest,
    )


def bar_chart(
    df: pd.DataFrame,
    path: Path,
    title: str,
    x_col: str = "metric_id",
    y_col: str = "value",
    annotate_values: bool = True,
    annotate_latest: bool = True,
    value_format: str | None = None,
) -> Path:
    fig, ax = plt.subplots(figsize=(9, 5))
    if df.empty or x_col not in df or y_col not in df:
        _empty(ax, title)
        return _save(fig, path)
    data = df.copy()
    bars = ax.bar(data[x_col].astype(str), pd.to_numeric(data[y_col], errors="coerce"), color="#4c78a8")
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.25)
    if annotate_values:
        fmt = value_format or infer_format(title)
        indices = range(len(bars)) if len(bars) <= 12 or not annotate_latest else [len(bars) - 1]
        for idx in indices:
            bar = bars[idx]
            height = bar.get_height()
            ax.annotate(
                format_value(height, fmt),
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
                color="#333333",
            )
    return _save(fig, path)


FX_RETURN_COLUMNS = ["1W_return_pct", "1M_return_pct", "3M_return_pct", "6M_return_pct", "YTD_return_pct"]
EQUITY_INDEX_IDS = [
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
]


def heatmap(
    df: pd.DataFrame,
    path: Path,
    title: str,
    value_columns: list[str] | None = None,
    value_suffix: str = "_return_pct",
) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if df.empty:
        _empty(ax, title)
        return _save(fig, path)
    value_cols = value_columns or [col for col in df.columns if col.endswith(value_suffix)]
    value_cols = [col for col in value_cols if col in df.columns]
    if not value_cols:
        _empty(ax, title)
        return _save(fig, path)
    data = df.set_index("metric_id")[value_cols]
    image = ax.imshow(data.fillna(0), aspect="auto", cmap="RdYlGn")
    ax.set_title(title)
    ax.set_yticks(range(len(data.index)), data.index)
    ax.set_xticks(range(len(value_cols)), [col.replace(value_suffix, "") for col in value_cols], rotation=30)
    fig.colorbar(image, ax=ax, label="%")
    return _save(fig, path)


def cross_market_yield_diff_heatmap(df: pd.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7, 4))
    if df.empty:
        _empty(ax, "Cross-Market Yield Differentials")
        return _save(fig, path)
    latest = _prep(df).sort_values("date").groupby("metric_id").tail(1)
    if latest.empty:
        _empty(ax, "Cross-Market Yield Differentials")
        return _save(fig, path)
    rows = []
    for _, item in latest.iterrows():
        pair, tenor = _split_yield_diff_id(str(item["metric_id"]))
        rows.append({"pair": pair, "tenor": tenor, "value": item["value"]})
    data = pd.DataFrame(rows).pivot_table(index="pair", columns="tenor", values="value", aggfunc="last")
    data = data.reindex(columns=[col for col in ["3M", "2Y", "10Y"] if col in data.columns])
    image = ax.imshow(data.fillna(0), aspect="auto", cmap="RdYlGn")
    ax.set_title("Cross-Market Yield Differentials")
    ax.set_yticks(range(len(data.index)), data.index)
    ax.set_xticks(range(len(data.columns)), data.columns)
    fig.colorbar(image, ax=ax, label="bps, local minus USD")
    return _save(fig, path)


def fed_corridor_chart(df: pd.DataFrame, path: Path) -> Path:
    return line_chart(df[df["metric_id"].isin(["sofr", "effr", "iorb"])] if not df.empty else df, path, "Fed Corridor")


def generate_dashboard_charts(
    raw: pd.DataFrame,
    curve_spreads: pd.DataFrame,
    fx_returns: pd.DataFrame,
    hibor_sofr_spreads: pd.DataFrame | None = None,
    price_returns: pd.DataFrame | None = None,
    factor_proxy_ratios: pd.DataFrame | None = None,
    sector_returns: pd.DataFrame | None = None,
    us_rate_spreads: pd.DataFrame | None = None,
    treasury_auction_calendar: pd.DataFrame | None = None,
    cross_market_yield_differentials: pd.DataFrame | None = None,
    output_dir: Path = CHART_DIR,
) -> list[Path]:
    if isinstance(us_rate_spreads, Path):
        output_dir = us_rate_spreads
        us_rate_spreads = None
    if isinstance(treasury_auction_calendar, Path):
        output_dir = treasury_auction_calendar
        treasury_auction_calendar = None
    if isinstance(cross_market_yield_differentials, Path):
        output_dir = cross_market_yield_differentials
        cross_market_yield_differentials = None
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = [
        normalized_line_chart(raw[raw["metric_id"].isin(["sp500", "nasdaq100"])] if not raw.empty else raw, output_dir / "equity_indices_normalized.png", "Equity Indices"),
        normalized_line_chart(raw[raw["metric_id"].isin(EQUITY_INDEX_IDS)] if not raw.empty else raw, output_dir / "global_equity_indices_normalized.png", "Global Equity Indices"),
        heatmap(price_returns if price_returns is not None else pd.DataFrame(), output_dir / "global_equity_indices_heatmap.png", "Global Equity Index Returns", value_columns=FX_RETURN_COLUMNS),
        line_chart(factor_proxy_ratios if factor_proxy_ratios is not None else pd.DataFrame(), output_dir / "factor_proxy_ratios.png", "Factor Proxy Ratios", value_format="level"),
        heatmap(sector_returns if sector_returns is not None else pd.DataFrame(), output_dir / "us_sector_heatmap.png", "US Sector ETF Returns", value_columns=FX_RETURN_COLUMNS),
        curve_chart(raw, output_dir / "ust_curve.png", "US Treasury Curve"),
        line_chart(curve_spreads, output_dir / "ust_curve_spreads.png", "UST Curve Spreads", id_col="spread_id", value_format="bps"),
        line_chart(curve_spreads, output_dir / "us_curve_spreads_expanded.png", "US Curve Spreads Expanded", id_col="spread_id", value_format="bps"),
        fed_corridor_chart(raw, output_dir / "fed_corridor.png"),
        line_chart(
            _combine_raw_and_spreads(raw, us_rate_spreads, ["sofr", "effr", "iorb", "on_rrp_rate", "obfr", "us_3m_tbill_yield"]),
            output_dir / "us_money_market_corridor.png",
            "US Money Market Corridor",
            value_format="percent",
        ),
        line_chart(
            _liquidity_stack_frame(raw),
            output_dir / "us_liquidity_stack.png",
            "US Liquidity Stack (USD bn)",
            value_format="usd_billions",
        ),
        line_chart(
            raw[raw["metric_id"].isin(["treasury_auction_bid_to_cover"])] if not raw.empty else raw,
            output_dir / "treasury_auction_bid_to_cover.png",
            "Treasury Auction Bid-to-Cover",
            value_format="level",
        ),
        line_chart(
            raw[
                raw["metric_id"].isin(
                    [
                        "treasury_auction_direct_bidders",
                        "treasury_auction_indirect_bidders",
                        "treasury_auction_primary_dealer_allocation",
                    ]
                )
            ] if not raw.empty else raw,
            output_dir / "treasury_auction_allocation.png",
            "Treasury Auction Allocation",
            value_format="percent",
        ),
        line_chart(
            raw[raw["metric_id"].isin(["treasury_auction_net_issuance"])] if not raw.empty else raw,
            output_dir / "treasury_net_issuance.png",
            "Treasury Net Issuance Proxy (USD bn)",
            value_format="usd_billions",
        ),
        line_chart(raw[raw["metric_id"].isin(["us_hy_oas", "us_ig_oas"])] if not raw.empty else raw, output_dir / "credit_spreads.png", "Credit Spreads", value_format="percent"),
        eu_yield_curve_chart(raw[raw["metric_id"].isin([item["metric_id"] for item in EUR_TENORS])] if not raw.empty else raw, output_dir / "eu_yield_curve.png"),
        line_chart(raw[raw["metric_id"].isin(["ecb_deposit_rate", "ecb_main_refi_rate", "ecb_marginal_lending_rate", "eur_on_rate"])] if not raw.empty else raw, output_dir / "ecb_policy_rates.png", "ECB Policy Rates", value_format="percent"),
        line_chart(raw[raw["metric_id"].isin(["eu_hy_oas", "eu_ig_oas"])] if not raw.empty else raw, output_dir / "eu_credit_spreads.png", "EU Credit Spreads", value_format="percent"),
        jp_jgb_curve_chart(raw[raw["metric_id"].isin([item["metric_id"] for item in JGB_TENORS])] if not raw.empty else raw, output_dir / "jp_jgb_curve.png"),
        line_chart(raw[raw["metric_id"].isin(["jgb_2y", "jgb_5y", "jgb_10y", "jgb_30y"])] if not raw.empty else raw, output_dir / "jp_jgb_yields.png", "Japan JGB Key Yields", value_format="percent"),
        heatmap(fx_returns, output_dir / "fx_spot_heatmap.png", "FX Spot Returns", value_columns=FX_RETURN_COLUMNS),
        hk_hibor_curve_chart(raw[raw["metric_id"].isin([item["metric_id"] for item in HIBOR_TENORS])] if not raw.empty else raw, output_dir / "hk_hibor_curve.png"),
        line_chart(raw[raw["metric_id"].isin(["hkma_aggregate_balance"])] if not raw.empty else raw, output_dir / "hkma_aggregate_balance.png", "HKMA Aggregate Balance (HKD mn)", value_format="money_hkd_mn"),
        line_chart(hibor_sofr_spreads if hibor_sofr_spreads is not None else pd.DataFrame(), output_dir / "hibor_sofr_spreads.png", "HIBOR - SOFR Proxy Spreads", id_col="metric_id", value_format="bps"),
        heatmap(fx_returns, output_dir / "fx_spot_expanded_heatmap.png", "Expanded FX Spot Returns", value_columns=FX_RETURN_COLUMNS),
        cross_market_yield_diff_heatmap(cross_market_yield_differentials if cross_market_yield_differentials is not None else pd.DataFrame(), output_dir / "cross_market_yield_differentials_heatmap.png"),
    ]
    cn_data = raw[raw["metric_id"].isin(["cgb_2y", "cgb_5y", "cgb_10y", "cgb_30y", "dr007", "fr007", "lpr", "mlf", "slf"])] if not raw.empty else raw
    if not cn_data.empty:
        paths.extend(
            [
                cn_cgb_curve_chart(cn_data, output_dir / "cn_cgb_curve.png"),
                line_chart(cn_data[cn_data["metric_id"].isin(["dr007", "fr007"])], output_dir / "cn_money_market_rates.png", "China Money Market Rates", value_format="percent"),
                line_chart(cn_data[cn_data["metric_id"].isin(["lpr", "mlf", "slf"])], output_dir / "cn_policy_rates.png", "China Policy Rates", value_format="percent"),
            ]
        )
    return paths


def _split_yield_diff_id(metric_id: str) -> tuple[str, str]:
    base = metric_id.replace("_yield_diff", "")
    pair, tenor = base.rsplit("_", 1)
    return pair.upper(), tenor.upper()


def _combine_raw_and_spreads(raw: pd.DataFrame, spreads: pd.DataFrame | None, metric_ids: list[str]) -> pd.DataFrame:
    frames = []
    if not raw.empty:
        frames.append(raw[raw["metric_id"].isin(metric_ids)])
    if spreads is not None and not spreads.empty:
        spread_frame = spreads.copy()
        spread_frame["value"] = pd.to_numeric(spread_frame["value"], errors="coerce") / 100
        frames.append(spread_frame[["date", "metric_id", "value"]])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", "metric_id", "value"])


def _liquidity_stack_frame(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return raw
    data = raw[raw["metric_id"].isin(["on_rrp_usage", "tga", "srf_usage", "bank_reserves"])].copy()
    if data.empty:
        return data
    data.loc[data["metric_id"].isin(["tga", "bank_reserves"]), "value"] = (
        pd.to_numeric(data.loc[data["metric_id"].isin(["tga", "bank_reserves"]), "value"], errors="coerce") / 1000
    )
    return data


def _prep(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    data = df.copy()
    data["date"] = pd.to_datetime(data["date"])
    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    return data.dropna(subset=["value"])


def _annotate_latest_lines(ax, plotted: list[tuple[Any, pd.DataFrame]], value_format: str) -> None:
    latest_points = []
    for line, group in plotted:
        valid = group.dropna(subset=["date", "value"]).sort_values("date")
        if valid.empty:
            continue
        point = valid.iloc[-1]
        latest_points.append((line, point["date"], point["value"]))
    latest_points.sort(key=lambda item: float(item[2]))
    for idx, (line, x_value, y_value) in enumerate(latest_points):
        offset = (idx - (len(latest_points) - 1) / 2) * 9
        ax.annotate(
            format_value(y_value, value_format),
            xy=(x_value, y_value),
            xytext=(8, offset),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=8,
            color=line.get_color(),
            bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "none", "alpha": 0.75},
        )
    if latest_points:
        ax.margins(x=0.08)


def _annotate_points(
    ax,
    labels: list[str],
    values: list[Any],
    value_format: str,
    indexes: list[int] | None = None,
) -> None:
    for idx in indexes if indexes is not None else range(len(values)):
        value = values[idx]
        if pd.isna(value):
            continue
        ax.annotate(
            format_value(value, value_format),
            xy=(labels[idx], value),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color="#333333",
        )


def _empty(ax, title: str) -> None:
    ax.set_title(title)
    ax.text(0.5, 0.5, "No data available", ha="center", va="center", transform=ax.transAxes)
    ax.set_axis_off()


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
