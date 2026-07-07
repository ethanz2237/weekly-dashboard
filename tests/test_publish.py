import json
from pathlib import Path

import pandas as pd

from dashboard.publish.layout import build_dashboard_layout
from dashboard.publish.markdown import render_markdown, write_dashboard


def _layout(tmp_path: Path):
    report = tmp_path / "source_validation_report.md"
    report.write_text("# Source Validation Report\n- Rows fetched: 2\n- Metrics present: 2\n")
    raw = pd.DataFrame(
        {
            "date": ["2026-07-01", "2026-07-01"],
            "metric_id": ["sp500", "eurusd"],
            "value": [100, 1.1],
        }
    )
    transforms = {
        "price_returns": pd.DataFrame([{"metric_id": "sp500", "latest_level": 100, "1W_return_pct": 1.2}]),
        "fx_returns": pd.DataFrame([{"metric_id": "eurusd", "latest_level": 1.1, "1W_return_pct": -0.5}]),
        "rate_changes": pd.DataFrame([{"metric_id": "sofr", "latest_level": 5, "1W_change_bps": 2}]),
        "curve_spreads": pd.DataFrame([{"date": "2026-07-01", "spread_id": "2s10s", "value": 35}]),
    }
    metrics = [
        {"metric_id": "sp500", "display_name": "S&P 500", "source": "public_market_data", "premium_required": False},
        {"metric_id": "eurusd", "display_name": "EURUSD", "source": "public_market_data", "premium_required": False},
        {"metric_id": "fx_implied_vol", "display_name": "FX Implied Vol", "source": "placeholder", "premium_required": True, "notes": "Premium placeholder."},
    ]
    return build_dashboard_layout(
        raw,
        transforms,
        metrics,
        metrics[:2],
        [Path("output/charts/equity_indices_normalized.png"), Path("output/charts/fx_spot_heatmap.png")],
        report,
        markdown_parent=Path("output"),
    )


def test_markdown_file_generation(tmp_path):
    layout = _layout(tmp_path)

    md_path, _ = write_dashboard(layout, tmp_path / "dashboard.md", tmp_path / "dashboard.json")

    assert md_path.exists()
    assert "Executive Snapshot" in md_path.read_text()


def test_json_layout_generation(tmp_path):
    layout = _layout(tmp_path)

    _, json_path = write_dashboard(layout, tmp_path / "dashboard.md", tmp_path / "dashboard.json")

    data = json.loads(json_path.read_text())
    assert data["sections"]["fx"]["fx_implied_vol"].startswith("Premium-required")


def test_missing_data_section_generation(tmp_path):
    layout = _layout(tmp_path)

    unavailable = layout["sections"]["missing_premium_required_data"]["unavailable_datasets"]
    premium = layout["sections"]["missing_premium_required_data"]["premium_required_datasets"]

    assert unavailable[0]["metric_id"] == "fx_implied_vol"
    assert premium[0]["premium_required"] is True


def test_chart_path_references(tmp_path):
    markdown = render_markdown(_layout(tmp_path))

    assert "(charts/equity_indices_normalized.png)" in markdown
    assert "(charts/fx_spot_heatmap.png)" in markdown
    assert "output/charts/equity_indices_normalized.png" not in markdown


def test_display_name_is_included_in_dashboard_tables(tmp_path):
    layout = _layout(tmp_path)

    row = layout["sections"]["equity"]["global_index_return_table"][0]

    assert row["metric_id"] == "sp500"
    assert row["display_name"] == "S&P 500"
