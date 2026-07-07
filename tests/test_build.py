import dashboard.run


def test_existing_mvp_build_still_works_with_expanded_catalog(monkeypatch, tmp_path):
    raw = dashboard.run._empty_normalized()
    raw.loc[0] = ["2026-07-01", "sp500", 100, "public_market_data", "yfinance", "2026-07-01"]
    outputs = {
        "price_returns": raw[["metric_id"]].assign(display_name="S&P 500", latest_level=100, **{"1W_return_pct": 1.0}),
        "sector_returns": raw.iloc[0:0],
        "factor_proxy_ratios": raw.iloc[0:0],
        "rate_changes": raw.iloc[0:0],
        "hk_rate_changes": raw.iloc[0:0],
        "curve_spreads": raw.iloc[0:0],
        "us_rate_spreads": raw.iloc[0:0],
        "hibor_sofr_spreads": raw.iloc[0:0],
        "fx_returns": raw.iloc[0:0],
        "treasury_auction_calendar_table": raw.iloc[0:0],
    }

    monkeypatch.setattr(dashboard.run, "ENV_PATH", tmp_path / ".env")
    monkeypatch.setattr(dashboard.run, "fetch_mvp_data", lambda metrics, as_of: (raw, []))
    monkeypatch.setattr(dashboard.run, "run_transforms", lambda raw_data, as_of: outputs)
    monkeypatch.setattr(dashboard.run, "generate_dashboard_charts", lambda *args, **kwargs: [tmp_path / "charts" / "equity_indices_normalized.png"])
    monkeypatch.setattr(dashboard.run, "write_dashboard", lambda layout, md_path: (tmp_path / "dashboard.md", tmp_path / "dashboard.json"))
    monkeypatch.setattr(dashboard.run, "write_report", lambda raw_data, metrics, issues, path=None: tmp_path / "source_validation_report.md")
    monkeypatch.setattr(dashboard.run, "parse_args", lambda: type("Args", (), {"mode": "build", "as_of": "latest"})())

    dashboard.run.main()
