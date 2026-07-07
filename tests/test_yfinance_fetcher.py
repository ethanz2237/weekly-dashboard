import pandas as pd

from dashboard.fetchers import yfinance_fetcher
from dashboard.utils import cache


def _metric(metric_id, ticker):
    return {
        "metric_id": metric_id,
        "source": "public_market_data",
        "provider": "yfinance",
        "ticker_or_series": ticker,
    }


def test_yfinance_fetcher_parses_mocked_response(monkeypatch):
    def fake_download(*args, **kwargs):
        return pd.DataFrame({"Close": [100.0, 101.0]}, index=pd.to_datetime(["2026-07-01", "2026-07-02"]))

    monkeypatch.setattr(yfinance_fetcher.yf, "download", fake_download)

    df, issues = yfinance_fetcher.fetch([_metric("csi300", "000300.SS")], "2026-07-02")

    assert issues == []
    assert list(df["metric_id"].unique()) == ["csi300"]
    assert df["value"].iloc[-1] == 101.0


def test_yfinance_fetcher_keeps_going_when_one_ticker_fails(monkeypatch):
    def fake_download(symbol, *args, **kwargs):
        if symbol == "BAD":
            raise RuntimeError("temporary outage")
        return pd.DataFrame({"Close": [1.0]}, index=pd.to_datetime(["2026-07-01"]))

    monkeypatch.setattr(yfinance_fetcher.yf, "download", fake_download)

    df, issues = yfinance_fetcher.fetch([_metric("bad", "BAD"), _metric("usdkrw", "KRW=X")], "2026-07-02")

    assert set(df["metric_id"]) == {"usdkrw"}
    assert any("bad" in issue for issue in issues)


def test_yfinance_fallback_ticker_succeeds(monkeypatch):
    calls = []

    def fake_download(symbol, *args, **kwargs):
        calls.append(symbol)
        if symbol == "^N225":
            return pd.DataFrame()
        return pd.DataFrame({"Close": [101.0]}, index=pd.to_datetime(["2026-07-01"]))

    monkeypatch.setattr(yfinance_fetcher.yf, "download", fake_download)

    df, issues = yfinance_fetcher.fetch([_metric("nikkei225", ["^N225", "1321.T"])], "2026-07-02")

    assert issues == []
    assert calls == ["^N225", "1321.T"]
    assert set(df["metric_id"]) == {"nikkei225"}
    assert set(df["ticker_used"]) == {"1321.T"}


def test_yfinance_all_tickers_fail_uses_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    cache.save_metric_cache(
        pd.DataFrame(
            [
                {
                    "date": "2026-07-01",
                    "metric_id": "topix",
                    "value": 2000.0,
                    "source": "public_market_data",
                    "provider": "yfinance",
                    "as_of_date": "2026-07-02",
                    "ticker_used": "1306.T",
                }
            ]
        )
    )
    monkeypatch.setattr(yfinance_fetcher.yf, "download", lambda *args, **kwargs: pd.DataFrame())

    df, issues = yfinance_fetcher.fetch([_metric("topix", ["^TOPX", "1306.T"])], "2026-07-02")

    assert not df.empty
    assert df["source_status"].iloc[0] == "cache_fallback"
    assert "cache fallback" in issues[0]


def test_yfinance_all_tickers_fail_without_cache_reports_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(yfinance_fetcher.yf, "download", lambda *args, **kwargs: pd.DataFrame())

    df, issues = yfinance_fetcher.fetch([_metric("topix", ["^TOPX", "1306.T"])], "2026-07-02")

    assert df.empty
    assert any("^TOPX" in issue for issue in issues)
    assert any("1306.T" in issue for issue in issues)
