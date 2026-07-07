import pandas as pd

import dashboard.run


def test_build_can_run_if_hkma_api_fails(monkeypatch, tmp_path):
    raw = dashboard.run._empty_normalized()
    raw.loc[0] = ["2026-07-01", "sp500", 100, "public_market_data", "yfinance", "2026-07-01"]
    outputs = {
        "price_returns": raw[["metric_id"]].assign(latest_level=100, **{"1W_return_pct": 1.0}),
        "rate_changes": pd.DataFrame(),
        "hk_rate_changes": pd.DataFrame(),
        "curve_spreads": pd.DataFrame(),
        "us_rate_spreads": pd.DataFrame(),
        "hibor_sofr_spreads": pd.DataFrame(),
        "fx_returns": pd.DataFrame(),
        "treasury_auction_calendar_table": pd.DataFrame(),
    }

    monkeypatch.setattr(dashboard.run, "ENV_PATH", tmp_path / ".env")
    monkeypatch.setenv("FRED_API_KEY", "test")
    monkeypatch.setattr(dashboard.run, "fetch_mvp_data", lambda metrics, as_of: (raw, ["HKMA HIBOR fetch failed: boom"]))
    monkeypatch.setattr(dashboard.run, "run_transforms", lambda raw_data, as_of: outputs)
    monkeypatch.setattr(dashboard.run, "generate_dashboard_charts", lambda *args, **kwargs: [tmp_path / "charts" / "hk_hibor_curve.png"])
    monkeypatch.setattr(dashboard.run, "write_dashboard", lambda layout, md_path: (tmp_path / "dashboard.md", tmp_path / "dashboard.json"))
    captured = {}

    def fake_report(raw_data, metrics, issues, path=None):
        captured["issues"] = issues
        return tmp_path / "source_validation_report.md"

    monkeypatch.setattr(dashboard.run, "write_report", fake_report)
    monkeypatch.setattr(dashboard.run, "parse_args", lambda: type("Args", (), {"mode": "build", "as_of": "latest"})())

    dashboard.run.main()

    assert captured["issues"] == ["HKMA HIBOR fetch failed: boom"]
