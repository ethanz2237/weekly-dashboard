import pandas as pd

from dashboard.fetchers import treasury_fetcher
from dashboard.utils import cache


METRICS = [
    {
        "metric_id": metric_id,
        "source": "Treasury FiscalData",
        "provider": "treasury",
        "implemented": True,
    }
    for metric_id in [
        "treasury_auction_net_issuance",
        "treasury_auction_bid_to_cover",
        "treasury_auction_direct_bidders",
        "treasury_auction_indirect_bidders",
        "treasury_auction_primary_dealer_allocation",
    ]
]


class _Response:
    def __init__(self, records):
        self.records = records

    def raise_for_status(self):
        return None

    def json(self):
        return {"data": self.records}


def _auction(date="2026-07-01"):
    return {
        "auction_date": date,
        "security_type": "Note",
        "security_term": "7-Year",
        "cusip": "91282AAA",
        "offering_amt": "44000000000",
        "currently_outstanding": "0",
        "est_pub_held_mat_by_type_amt": "4000000000",
        "total_accepted": "44000000000",
        "bid_to_cover_ratio": "2.58",
        "direct_bidder_accepted": "4400000000",
        "indirect_bidder_accepted": "28600000000",
        "primary_dealer_accepted": "11000000000",
    }


def test_treasury_fetcher_parses_fiscaldata_response(monkeypatch):
    monkeypatch.setattr(treasury_fetcher, "get_json", lambda *args, **kwargs: _Response([_auction()]).json())

    frame, issues = treasury_fetcher.fetch(METRICS, "2026-07-02")

    assert not issues
    values = dict(zip(frame["metric_id"], frame["value"], strict=False))
    assert values["treasury_auction_bid_to_cover"] == 2.58
    assert values["treasury_auction_net_issuance"] == 40.0
    assert values["treasury_auction_direct_bidders"] == 10.0
    assert values["treasury_auction_indirect_bidders"] == 65.0
    assert values["treasury_auction_primary_dealer_allocation"] == 25.0
    assert {"security_type", "security_term", "cusip"} <= set(frame.columns)


def test_treasury_fetcher_respects_as_of(monkeypatch):
    records = [_auction("2026-07-01"), _auction("2026-07-10")]
    monkeypatch.setattr(treasury_fetcher, "get_json", lambda *args, **kwargs: _Response(records).json())

    frame, _ = treasury_fetcher.fetch(METRICS, "2026-07-02")

    assert set(pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")) == {"2026-07-01"}


def test_treasury_fetcher_failure_is_nonfatal(monkeypatch, tmp_path):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)

    def fail(*args, **kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(treasury_fetcher, "get_json", fail)

    frame, issues = treasury_fetcher.fetch(METRICS, "2026-07-02")

    assert frame.empty
    assert "Treasury FiscalData auction fetch failed" in issues[0]
