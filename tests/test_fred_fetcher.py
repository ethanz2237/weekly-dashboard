from datetime import date

from dashboard.fetchers import fred_fetcher


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {"observations": [{"date": "2026-07-01", "value": "4.5"}]}


def test_fred_fetcher_sets_observation_end_for_latest_mode(monkeypatch):
    captured = {}
    metric = {
        "metric_id": "us_10y_yield",
        "ticker_or_series": "DGS10",
        "source": "FRED",
        "provider": "fred",
    }

    def fake_json(url, params, timeout):
        captured["params"] = params
        return _Response().json()

    monkeypatch.setenv("FRED_API_KEY", "abc123")
    monkeypatch.setattr(fred_fetcher, "get_json", fake_json)

    fred_fetcher.fetch([metric], "latest")

    assert captured["params"]["observation_end"] == date.today().isoformat()
