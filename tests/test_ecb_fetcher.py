from dashboard.fetchers import ecb_fetcher
from dashboard.utils import cache


def _metric(metric_id="eur_10y_yield", series="YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y"):
    return {
        "metric_id": metric_id,
        "source": "ECB Data Portal",
        "provider": "ecb",
        "ticker_or_series": series,
        "implemented": True,
    }


def test_ecb_fetcher_parses_csv(monkeypatch):
    def fake_text(url, params, timeout):
        assert "YC/" in url
        assert params["endPeriod"] == "2026-07-02"
        return "TIME_PERIOD,OBS_VALUE\n2026-07-01,2.5\n"

    monkeypatch.setattr(ecb_fetcher, "get_text", fake_text)

    df, issues = ecb_fetcher.fetch([_metric()], "2026-07-02")

    assert not issues
    assert df.loc[0, "metric_id"] == "eur_10y_yield"
    assert df.loc[0, "value"] == 2.5


def test_ecb_fetcher_uses_cache_on_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    cached = ecb_fetcher._parse_csv("TIME_PERIOD,OBS_VALUE\n2026-07-01,2.5\n", _metric(), "2026-07-02")
    cache.save_metric_cache(cached)

    def fail(*args, **kwargs):
        raise RuntimeError("ECB unavailable")

    monkeypatch.setattr(ecb_fetcher, "get_text", fail)
    monkeypatch.setattr(ecb_fetcher, "load_metric_cache", cache.load_metric_cache)

    df, issues = ecb_fetcher.fetch([_metric()], "2026-07-02")

    assert not df.empty
    assert df.loc[0, "source_status"] == "cache_fallback"
    assert "used cache fallback" in issues[0]
