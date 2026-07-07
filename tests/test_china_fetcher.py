import pandas as pd

from dashboard.fetchers import china_fetcher


def _metric(metric_id="cgb_10y"):
    return {
        "metric_id": metric_id,
        "source": "manual CSV fallback",
        "provider": "manual_china",
        "ticker_or_series": metric_id,
        "implemented": True,
    }


def test_china_manual_csv_respects_as_of(tmp_path):
    path = tmp_path / "china_rates.csv"
    path.write_text(
        "date,metric_id,value,source,provider,notes\n"
        "2026-07-01,cgb_10y,2.2,manual_csv,manual_china,\n"
        "2026-07-03,cgb_10y,9.9,manual_csv,manual_china,\n"
    )

    df = china_fetcher.read_manual_csv(path, "2026-07-02")

    assert list(df["value"]) == [2.2]


def test_china_fetcher_reads_manual_csv(monkeypatch, tmp_path):
    path = tmp_path / "china_rates.csv"
    path.write_text("date,metric_id,value,source,provider,notes\n2026-07-01,cgb_10y,2.2,manual_csv,manual_china,\n")
    monkeypatch.setattr(china_fetcher, "MANUAL_CHINA_RATES", path)

    df, issues = china_fetcher.fetch([_metric()], "2026-07-02")

    assert not issues
    assert df.loc[0, "metric_id"] == "cgb_10y"
    assert df.loc[0, "source_status"] == "manual"


def test_china_fetcher_missing_manual_file_reports_issue(monkeypatch, tmp_path):
    monkeypatch.setattr(china_fetcher, "MANUAL_CHINA_RATES", tmp_path / "missing.csv")
    monkeypatch.setattr(china_fetcher, "load_metric_cache", lambda *args, **kwargs: pd.DataFrame())

    df, issues = china_fetcher.fetch([_metric()], "2026-07-02")

    assert df.empty
    assert "no China manual CSV observations" in issues[0]
