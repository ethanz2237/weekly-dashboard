import pandas as pd

from dashboard.fetchers import hkma_fetcher
from dashboard.utils import cache


class _Response:
    def __init__(self, records):
        self.records = records

    def raise_for_status(self):
        return None

    def json(self):
        return {"result": {"datasize": len(self.records), "records": self.records}}


def _metric(metric_id, ticker="TBD"):
    return {
        "metric_id": metric_id,
        "source": "HKMA official API",
        "provider": "hkma",
        "ticker_or_series": ticker,
    }


def test_hkma_fetcher_parses_hibor_response(monkeypatch):
    def fake_json(url, params, headers, timeout):
        if params["offset"] > 0:
            return _Response([]).json()
        return _Response(
            [
                {
                    "end_of_day": "2026-07-01",
                    "ir_overnight": "2.1",
                    "ir_1w": "2.2",
                    "ir_1m": "2.3",
                    "ir_3m": "2.4",
                    "ir_6m": "2.5",
                    "ir_12m": "2.6",
                }
            ]
        ).json()

    monkeypatch.setattr(hkma_fetcher, "get_json", fake_json)

    df, issues = hkma_fetcher.fetch([_metric("hibor_on"), _metric("hibor_3m")], "2026-07-02")

    assert not issues
    assert set(df["metric_id"]) == {"hibor_on", "hibor_3m"}
    assert df.loc[df["metric_id"] == "hibor_3m", "value"].iloc[0] == 2.4


def test_hkma_fetcher_parses_aggregate_balance_response(monkeypatch):
    def fake_json(url, params, headers, timeout):
        if params["offset"] > 0:
            return _Response([]).json()
        return _Response([{"end_of_date": "2026-07-01", "aggr_balance_af_disc_win": "44,000"}]).json()

    monkeypatch.setattr(hkma_fetcher, "get_json", fake_json)

    df, issues = hkma_fetcher.fetch([_metric("hkma_aggregate_balance", "aggr_balance_af_disc_win")], "2026-07-02")

    assert not issues
    assert df.loc[0, "metric_id"] == "hkma_aggregate_balance"
    assert df.loc[0, "value"] == 44000


def test_hkma_fetcher_parses_actual_aggregate_balance_field_names(monkeypatch):
    def fake_json(url, params, headers, timeout):
        if params["offset"] > 0:
            return _Response([]).json()
        return _Response(
            [
                {
                    "end_of_date": "2026-07-03",
                    "cert_of_indebt": 658435,
                    "aggr_balance_bf_disc_win": 54157,
                    "aggr_balance_af_disc_win": 54527,
                    "mb_bf_disc_win_total": 2076763,
                }
            ]
        ).json()

    monkeypatch.setattr(hkma_fetcher, "get_json", fake_json)

    df, issues = hkma_fetcher.fetch([_metric("hkma_aggregate_balance", "aggr_balance_af_disc_win")], "2026-07-05")

    assert not issues
    assert df.loc[0, "value"] == 54527


def test_hkma_fetcher_parses_hk_mn_string_values(monkeypatch):
    def fake_json(url, params, headers, timeout):
        if params["offset"] > 0:
            return _Response([]).json()
        return _Response([{"end_of_date": "2026-07-03", "Aggregate Balance (after Discount Window)": "HK$ 54,527 mn"}]).json()

    monkeypatch.setattr(hkma_fetcher, "get_json", fake_json)

    df, issues = hkma_fetcher.fetch([_metric("hkma_aggregate_balance")], "2026-07-05")

    assert not issues
    assert df.loc[0, "value"] == 54527


def test_hkma_fetcher_reports_available_keys_when_aggregate_field_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)

    def fake_json(url, params, headers, timeout):
        if params["offset"] > 0:
            return _Response([]).json()
        return _Response([{"end_of_date": "2026-07-03", "some_other_field": 1}]).json()

    monkeypatch.setattr(hkma_fetcher, "get_json", fake_json)

    df, issues = hkma_fetcher.fetch([_metric("hkma_aggregate_balance")], "2026-07-05")

    assert df.empty
    assert "Available keys:" in issues[0]
    assert "some_other_field" in issues[0]


def test_hkma_fetcher_as_of_filter_excludes_future_dates(monkeypatch):
    def fake_json(url, params, headers, timeout):
        if params["offset"] > 0:
            return _Response([]).json()
        return _Response(
            [
                {"end_of_day": "2026-07-01", "ir_3m": "2.4"},
                {"end_of_day": "2026-07-03", "ir_3m": "9.9"},
            ]
        ).json()

    monkeypatch.setattr(hkma_fetcher, "get_json", fake_json)

    df, _ = hkma_fetcher.fetch([_metric("hibor_3m")], "2026-07-02")

    assert list(pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")) == ["2026-07-01"]
