import pandas as pd
import requests

import dashboard.run
from dashboard.fetchers import fred_fetcher, hkma_fetcher, treasury_fetcher
from dashboard.utils import cache
from dashboard.utils.http import get_json
from dashboard.utils.sanitize import sanitize
from dashboard.utils.validation import write_report


def test_credential_sanitizer_removes_api_key_from_urls(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "abcdef123456")
    text = "https://api.stlouisfed.org/fred/series/observations?series_id=DGS2&api_key=abcdef123456"

    assert sanitize(text) == "https://api.stlouisfed.org/fred/series/observations?series_id=DGS2&api_key=***"


def test_validation_report_sanitizes_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "abcdef123456")
    path = write_report(pd.DataFrame(), [], ["failed with api_key=abcdef123456"], tmp_path / "report.md")

    text = path.read_text()
    assert "abcdef123456" not in text
    assert "***" in text


def test_cache_fallback_metric_is_not_reported_missing(tmp_path):
    df = pd.DataFrame(
        [{"date": "2026-07-01", "metric_id": "us_2y_yield", "value": 4.0, "source_status": "cache_fallback"}]
    )
    metrics = [{"metric_id": "us_2y_yield", "implemented": True}]

    path = write_report(df, metrics, [], tmp_path / "report.md")

    text = path.read_text()
    assert "## Implemented But Missing\nNone" in text
    assert "## Present Via Cache Fallback\n- us_2y_yield" in text


def test_http_retry_502_then_success(monkeypatch):
    calls = {"count": 0}

    class Response:
        def __init__(self, status):
            self.status_code = status

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError("boom")

        def json(self):
            return {"ok": True}

    class Session:
        def get(self, *args, **kwargs):
            calls["count"] += 1
            return Response(502 if calls["count"] == 1 else 200)

    monkeypatch.setattr(requests, "Session", Session)
    monkeypatch.setattr("dashboard.utils.http.time.sleep", lambda _: None)

    assert get_json("https://example.test") == {"ok": True}
    assert calls["count"] == 2


def test_fred_single_series_failure_uses_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    monkeypatch.setenv("FRED_API_KEY", "abcdef123456")
    cache.save_metric_cache(
        pd.DataFrame([{"date": "2026-07-01", "metric_id": "us_2y_yield", "value": 4.0, "source": "FRED", "provider": "fred", "as_of_date": "2026-07-02"}])
    )
    monkeypatch.setattr(fred_fetcher, "get_json", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("FRED 502 api_key=abcdef123456")))

    frame, issues = fred_fetcher.fetch(
        [{"metric_id": "us_2y_yield", "ticker_or_series": "DGS2", "source": "FRED", "provider": "fred", "frequency": "daily"}],
        "2026-07-02",
    )

    assert not frame.empty
    assert frame["source_status"].iloc[0] == "cache_fallback"
    assert "abcdef123456" not in issues[0]


def test_hkma_hibor_timeout_uses_cached_fixing_data(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    cache.save_metric_cache(
        pd.DataFrame([{"date": "2026-07-01", "metric_id": "hibor_3m", "value": 2.4, "source": "HKMA", "provider": "hkma", "as_of_date": "2026-07-02"}])
    )
    monkeypatch.setattr(hkma_fetcher, "get_json", lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("timeout")))

    frame, issues = hkma_fetcher.fetch([{"metric_id": "hibor_3m", "source": "HKMA", "provider": "hkma"}], "2026-07-02")

    assert set(frame["metric_id"]) == {"hibor_3m"}
    assert frame["source_status"].iloc[0] == "cache_fallback"
    assert "cache fallback" in issues[0]


def test_treasury_failure_uses_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    cache.save_metric_cache(
        pd.DataFrame([{"date": "2026-07-01", "metric_id": "treasury_auction_bid_to_cover", "value": 2.5, "source": "Treasury FiscalData", "provider": "treasury", "as_of_date": "2026-07-02"}])
    )
    monkeypatch.setattr(treasury_fetcher, "get_json", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("disconnect")))

    frame, issues = treasury_fetcher.fetch(
        [{"metric_id": "treasury_auction_bid_to_cover", "source": "Treasury FiscalData", "provider": "treasury", "implemented": True}],
        "2026-07-02",
    )

    assert not frame.empty
    assert frame["source_status"].iloc[0] == "cache_fallback"
    assert "cache fallback" in issues[0]


def test_source_health_command(monkeypatch, capsys):
    monkeypatch.setattr(dashboard.run, "get_json", lambda *args, **kwargs: {"ok": True})
    monkeypatch.setattr(dashboard.run, "get_text", lambda *args, **kwargs: "ok")
    monkeypatch.setattr(dashboard.run, "cache_available", lambda *args, **kwargs: False)

    dashboard.run.source_health()

    output = capsys.readouterr().out
    assert "FRED DGS10: OK" in output
    assert "Treasury FiscalData: OK" in output
    assert "ECB EUR 10Y: OK" in output
    assert "Japan MOF JGB: OK" in output
