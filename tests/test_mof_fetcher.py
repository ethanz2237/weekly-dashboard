from dashboard.fetchers import mof_fetcher


def _metric(metric_id="jgb_10y", tenor="10Y"):
    return {
        "metric_id": metric_id,
        "source": "Japan MOF",
        "provider": "mof",
        "ticker_or_series": tenor,
        "implemented": True,
    }


CSV = """Interest Rate,,,,(Unit : %)
Date,1Y,2Y,5Y,10Y,30Y
2026/7/1,1.1,1.4,1.9,2.7,3.8
2026/7/2,1.2,1.5,2.0,2.8,3.9
"""


def test_mof_fetcher_parses_jgb_csv(monkeypatch):
    monkeypatch.setattr(mof_fetcher, "get_text", lambda *args, **kwargs: CSV)

    df, issues = mof_fetcher.fetch([_metric()], "2026-07-02")

    assert not issues
    assert list(df["value"]) == [2.7, 2.8]
    assert set(df["metric_id"]) == {"jgb_10y"}


def test_mof_fetcher_respects_as_of(monkeypatch):
    monkeypatch.setattr(mof_fetcher, "get_text", lambda *args, **kwargs: CSV)

    df, _ = mof_fetcher.fetch([_metric("jgb_2y", "2Y")], "2026-07-01")

    assert list(df["value"]) == [1.4]
