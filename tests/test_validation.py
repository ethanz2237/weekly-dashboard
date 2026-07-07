import pandas as pd

from dashboard.utils.validation import missing_credentials, missing_series, planned_unimplemented, premium_required, stale_series, write_report


def test_stale_data_check():
    df = pd.DataFrame({"date": ["2000-01-01"], "metric_id": ["sp500"], "value": [100]})

    assert stale_series(df, max_age_days=10) == ["sp500"]


def test_missing_source_handling():
    df = pd.DataFrame({"date": ["2026-07-01"], "metric_id": ["sp500"], "value": [100]})
    metrics = [{"metric_id": "sp500"}, {"metric_id": "us_10y_yield"}]

    assert missing_series(df, metrics) == ["us_10y_yield"]


def test_planned_metrics_are_not_missing_data_errors():
    df = pd.DataFrame({"date": ["2026-07-01"], "metric_id": ["sp500"], "value": [100]})
    metrics = [
        {"metric_id": "sp500", "implemented": True, "provider": "yfinance"},
        {"metric_id": "csi300", "implemented": False, "provider": "yfinance"},
    ]

    assert missing_series(df, metrics) == []


def test_premium_required_metrics_are_reported_separately(tmp_path):
    metrics = [
        {"metric_id": "sp500", "implemented": True, "provider": "yfinance", "premium_required": False},
        {"metric_id": "eurusd_3m_implied_vol", "implemented": False, "provider": "tbd", "premium_required": True},
    ]

    report = write_report(
        pd.DataFrame({"date": ["2026-07-01"], "metric_id": ["sp500"], "value": [100]}),
        metrics,
        [],
        tmp_path / "report.md",
    )
    text = report.read_text()

    assert premium_required(metrics) == ["eurusd_3m_implied_vol"]
    assert planned_unimplemented(metrics) == []
    assert "## Planned But Not Implemented" in text
    assert "## Premium Required" in text
    assert "- eurusd_3m_implied_vol" in text


def test_deprecated_metrics_are_reported_separately(tmp_path):
    metrics = [
        {"metric_id": "old_placeholder", "implemented": False, "provider": "tbd", "premium_required": False, "deprecated": True}
    ]

    report = write_report(pd.DataFrame(), metrics, [], tmp_path / "report.md")
    text = report.read_text()

    assert "## Deprecated" in text
    assert "- old_placeholder" in text
    assert planned_unimplemented(metrics) == []


def test_validation_report_grouping_works_for_hkma_metrics(tmp_path):
    metrics = [
        {"metric_id": "hibor_3m", "implemented": True, "provider": "hkma", "premium_required": False},
        {"metric_id": "hkma_aggregate_balance", "implemented": True, "provider": "hkma", "premium_required": False},
    ]
    df = pd.DataFrame({"date": ["2026-07-01"], "metric_id": ["hibor_3m"], "value": [2.4]})

    report = write_report(df, metrics, [], tmp_path / "report.md").read_text()

    assert "## Implemented And Present\n- hibor_3m" in report
    assert "## Implemented But Missing\n- hkma_aggregate_balance" in report


def test_missing_credentials():
    metrics = [{"metric_id": "us_10y_yield", "provider": "fred"}]

    assert missing_credentials(metrics, {}) == ["FRED_API_KEY"]
