from pathlib import Path

import pandas as pd

from dashboard.charts import matplotlib_charts
from dashboard.charts.formatting import format_value
from dashboard.charts.matplotlib_charts import (
    FX_RETURN_COLUMNS,
    UST_TENORS,
    bar_chart,
    curve_chart,
    generate_dashboard_charts,
    line_chart,
    normalized_line_chart,
    snapshot_curve_chart,
)


def test_chart_file_generation_with_mock_data(tmp_path: Path):
    df = pd.DataFrame(
        {
            "date": ["2026-07-01", "2026-07-02"],
            "metric_id": ["sp500", "sp500"],
            "value": [100, 101],
        }
    )

    path = normalized_line_chart(df, tmp_path / "chart.png", "Test Chart")

    assert path.exists()
    assert path.stat().st_size > 0


def test_fx_heatmap_excludes_usd_strength_adjusted_columns(monkeypatch, tmp_path: Path):
    captured = {}

    def fake_heatmap(df, path, title, value_columns=None, value_suffix="_return_pct"):
        captured["value_columns"] = value_columns
        return path

    monkeypatch.setattr(matplotlib_charts, "heatmap", fake_heatmap)
    fx_returns = pd.DataFrame(
        [
            {
                "metric_id": "eurusd",
                "1W_return_pct": 1.0,
                "usd_strength_adjusted_1W_return_pct": -1.0,
            }
        ]
    )

    generate_dashboard_charts(pd.DataFrame(), pd.DataFrame(), fx_returns, pd.DataFrame(), tmp_path)

    assert captured["value_columns"] == FX_RETURN_COLUMNS
    assert "usd_strength_adjusted_1W_return_pct" not in captured["value_columns"]


def test_expanded_chart_files_generate_with_mock_data(tmp_path: Path):
    raw = pd.DataFrame(
        {
            "date": ["2026-07-01", "2026-07-02"] * 2,
            "metric_id": ["sp500", "sp500", "csi300", "csi300"],
            "value": [100, 101, 200, 198],
        }
    )
    returns = pd.DataFrame(
        [
            {"metric_id": "sp500", "1W_return_pct": 1.0, "1M_return_pct": 2.0},
            {"metric_id": "csi300", "1W_return_pct": -1.0, "1M_return_pct": 1.0},
        ]
    )
    factors = pd.DataFrame(
        {
            "date": ["2026-07-01", "2026-07-02"],
            "metric_id": ["growth_vs_value_proxy", "growth_vs_value_proxy"],
            "value": [100, 101],
        }
    )

    paths = generate_dashboard_charts(
        raw,
        pd.DataFrame(),
        returns,
        pd.DataFrame(),
        returns,
        factors,
        returns,
        tmp_path,
    )

    names = {path.name for path in paths}
    assert "global_equity_indices_heatmap.png" in names
    assert "global_equity_indices_normalized.png" in names
    assert "factor_proxy_ratios.png" in names
    assert "us_sector_heatmap.png" in names
    assert "fx_spot_expanded_heatmap.png" in names
    assert "us_money_market_corridor.png" in names
    assert "us_liquidity_stack.png" in names
    assert "us_curve_spreads_expanded.png" in names
    assert "treasury_auction_bid_to_cover.png" in names
    assert "treasury_auction_allocation.png" in names
    assert "treasury_net_issuance.png" in names
    assert "eu_yield_curve.png" in names
    assert "ecb_policy_rates.png" in names
    assert "eu_credit_spreads.png" in names
    assert "jp_jgb_curve.png" in names
    assert "jp_jgb_yields.png" in names
    assert "cross_market_yield_differentials_heatmap.png" in names


def test_china_charts_generate_when_manual_data_exists(tmp_path: Path):
    rows = []
    for metric_id, value in [
        ("cgb_2y", 1.8),
        ("cgb_5y", 2.0),
        ("cgb_10y", 2.2),
        ("cgb_30y", 2.6),
        ("dr007", 1.7),
        ("fr007", 1.9),
        ("lpr", 3.0),
    ]:
        rows.append({"date": "2026-07-01", "metric_id": metric_id, "value": value})

    paths = generate_dashboard_charts(pd.DataFrame(rows), pd.DataFrame(), pd.DataFrame(), output_dir=tmp_path)
    names = {path.name for path in paths}

    assert "cn_cgb_curve.png" in names
    assert "cn_money_market_rates.png" in names
    assert "cn_policy_rates.png" in names


def test_value_formatting_helpers():
    assert format_value(4.281, "percent") == "4.28%"
    assert format_value(12.2, "bps") == "+12bp"
    assert format_value(-8.2, "bps") == "-8bp"
    assert format_value(44900, "money_hkd_mn") == "HK$44.9bn"
    assert format_value("abc", "raw") == "abc"


def test_line_chart_annotation_creates_text_labels(monkeypatch, tmp_path: Path):
    texts = []

    def fake_save(fig, path):
        texts.extend(text.get_text() for ax in fig.axes for text in ax.texts)
        return path

    monkeypatch.setattr(matplotlib_charts, "_save", fake_save)
    df = pd.DataFrame(
        {
            "date": ["2026-07-01", "2026-07-02", "2026-07-01", "2026-07-02"],
            "metric_id": ["a", "a", "b", "b"],
            "value": [1.0, 1.2, 2.0, 2.3],
        }
    )

    line_chart(df, tmp_path / "line.png", "Rate Chart", value_format="percent")

    assert "1.20%" in texts
    assert "2.30%" in texts


def test_bar_chart_annotation_creates_labels(monkeypatch, tmp_path: Path):
    texts = []

    def fake_save(fig, path):
        texts.extend(text.get_text() for ax in fig.axes for text in ax.texts)
        return path

    monkeypatch.setattr(matplotlib_charts, "_save", fake_save)
    df = pd.DataFrame({"metric_id": ["a", "b"], "value": [10, 20]})

    bar_chart(df, tmp_path / "bar.png", "Bar Chart", value_format="integer")

    assert "10" in texts
    assert "20" in texts


def test_bar_chart_saves_successfully(tmp_path: Path):
    df = pd.DataFrame({"metric_id": ["a", "b"], "value": [10, 20]})

    path = bar_chart(df, tmp_path / "bar.png", "Bar Chart")

    assert path.exists()
    assert path.stat().st_size > 0


def test_curve_chart_uses_full_ust_ladder_and_snapshots(monkeypatch, tmp_path: Path):
    captured = {"lines": [], "texts": []}

    def fake_save(fig, path):
        ax = fig.axes[0]
        captured["lines"] = [list(line.get_xdata()) for line in ax.lines]
        captured["texts"] = [text.get_text() for text in ax.texts]
        return path

    monkeypatch.setattr(matplotlib_charts, "_save", fake_save)
    rows = []
    for date, base in [("2026-06-01", 3.8), ("2026-06-24", 4.0), ("2026-07-01", 4.1)]:
        for idx, tenor in enumerate(UST_TENORS):
            rows.append({"date": date, "metric_id": tenor["metric_id"], "value": base + idx / 100})
    df = pd.DataFrame(rows)

    curve_chart(df, tmp_path / "ust_curve.png", "US Treasury Curve")

    assert len(captured["lines"]) == 3
    assert captured["lines"][0] == ["1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"]
    assert any(label.endswith("%") for label in captured["texts"])


def test_curve_chart_respects_tenor_order(monkeypatch, tmp_path: Path):
    captured = {}

    def fake_save(fig, path):
        captured["xdata"] = list(fig.axes[0].lines[0].get_xdata())
        return path

    monkeypatch.setattr(matplotlib_charts, "_save", fake_save)
    tenors = [
        {"metric_id": "c", "tenor": "30Y", "tenor_order": 3, "highlight": False},
        {"metric_id": "a", "tenor": "1Y", "tenor_order": 1, "highlight": False},
        {"metric_id": "b", "tenor": "10Y", "tenor_order": 2, "highlight": True},
    ]
    df = pd.DataFrame(
        [
            {"date": "2026-07-01", "metric_id": "a", "value": 1.0},
            {"date": "2026-07-01", "metric_id": "b", "value": 2.0},
            {"date": "2026-07-01", "metric_id": "c", "value": 3.0},
        ]
    )

    snapshot_curve_chart(df, tmp_path / "curve.png", "Curve", tenors)

    assert captured["xdata"] == ["1Y", "10Y", "30Y"]
