from pathlib import Path

import yaml


REQUIRED_FIELDS = {
    "metric_id",
    "display_name",
    "asset_class",
    "region",
    "group",
    "source",
    "provider",
    "ticker_or_series",
    "frequency",
    "unit",
    "transform",
    "chart_type",
    "fallback_source",
    "premium_required",
    "implemented",
    "notes",
}

MVP_IMPLEMENTED = {
    "sp500",
    "nasdaq100",
    "csi300",
    "chinext",
    "hsi",
    "hstech",
    "stoxx50",
    "stoxx600",
    "nikkei225",
    "topix",
    "kospi",
    "twse",
    "nifty50",
    "idx",
    "growth_vs_value_proxy",
    "defensives_vs_cyclicals_proxy",
    "us_sector_etf_heatmap",
    "us_1m_yield",
    "us_3m_yield",
    "us_6m_yield",
    "us_1y_yield",
    "us_2y_yield",
    "us_3y_yield",
    "us_5y_yield",
    "us_7y_yield",
    "us_10y_yield",
    "us_20y_yield",
    "us_30y_yield",
    "us_2s10s",
    "us_5s30s",
    "us_10s30s",
    "us_3m_tbill_yield",
    "sofr",
    "effr",
    "iorb",
    "on_rrp_rate",
    "on_rrp_usage",
    "obfr",
    "sofr_minus_effr",
    "iorb_minus_effr",
    "tga",
    "srf_usage",
    "bank_reserves",
    "treasury_auction_net_issuance",
    "treasury_auction_bid_to_cover",
    "treasury_auction_direct_bidders",
    "treasury_auction_indirect_bidders",
    "treasury_auction_primary_dealer_allocation",
    "us_hy_oas",
    "us_ig_oas",
    "eurusd",
    "usdjpy",
    "usdhkd",
    "usdkrw",
    "usdtwd",
    "usdcny",
    "cnycnh",
    "usdidr",
    "usdinr",
}


def test_metrics_catalog_exists():
    assert Path("config/metrics_catalog.yml").exists()


def test_each_metric_has_required_fields():
    catalog = yaml.safe_load(Path("config/metrics_catalog.yml").read_text())

    assert isinstance(catalog["metrics"], list)
    assert catalog["metrics"]

    for metric in catalog["metrics"]:
        assert REQUIRED_FIELDS <= metric.keys(), metric["metric_id"]


def test_catalog_has_expected_production_metrics():
    metrics = yaml.safe_load(Path("config/metrics_catalog.yml").read_text())["metrics"]
    ids = {metric["metric_id"] for metric in metrics}

    for metric_id in ["csi300", "hibor_3m", "hkma_aggregate_balance", "cgb_10y", "jgb_10y", "eur_10y_yield", "eurusd_3m_implied_vol", "usdcnh_cross_currency_basis"]:
        assert metric_id in ids


def test_generic_legacy_placeholders_removed_from_active_catalog():
    metrics = yaml.safe_load(Path("config/metrics_catalog.yml").read_text())["metrics"]
    ids = {metric["metric_id"] for metric in metrics}

    assert "fx_implied_vol" not in ids
    assert "cross_currency_basis" not in ids


def test_implemented_flag_marks_mvp_metrics():
    metrics = yaml.safe_load(Path("config/metrics_catalog.yml").read_text())["metrics"]
    by_id = {metric["metric_id"]: metric for metric in metrics}

    for metric_id in MVP_IMPLEMENTED:
        assert by_id[metric_id]["implemented"] is True

    assert by_id["csi300"]["implemented"] is True


def test_full_ust_curve_tenor_list_is_cataloged():
    metrics = yaml.safe_load(Path("config/metrics_catalog.yml").read_text())["metrics"]
    curve = [m for m in metrics if m.get("curve_group") == "us_treasury_curve" and m.get("is_curve_tenor")]

    assert [m["metric_id"] for m in sorted(curve, key=lambda m: m["tenor_order"])] == [
        "us_1m_yield",
        "us_3m_yield",
        "us_6m_yield",
        "us_1y_yield",
        "us_2y_yield",
        "us_3y_yield",
        "us_5y_yield",
        "us_7y_yield",
        "us_10y_yield",
        "us_20y_yield",
        "us_30y_yield",
    ]
    assert {m["metric_id"] for m in curve if m.get("highlight_on_curve")} == {
        "us_2y_yield",
        "us_5y_yield",
        "us_10y_yield",
        "us_30y_yield",
    }


def test_hibor_curve_supports_full_available_tenor_ladder():
    metrics = yaml.safe_load(Path("config/metrics_catalog.yml").read_text())["metrics"]
    curve = [m for m in metrics if m.get("curve_group") == "hk_hibor_curve" and m.get("is_curve_tenor")]

    assert [m["metric_id"] for m in sorted(curve, key=lambda m: m["tenor_order"])] == [
        "hibor_on",
        "hibor_1w",
        "hibor_1m",
        "hibor_3m",
        "hibor_6m",
        "hibor_12m",
    ]
    assert {m["metric_id"] for m in curve if m.get("highlight_on_curve")} == {
        "hibor_on",
        "hibor_1m",
        "hibor_3m",
        "hibor_6m",
    }


def test_eur_curve_supports_full_available_tenor_ladder():
    metrics = yaml.safe_load(Path("config/metrics_catalog.yml").read_text())["metrics"]
    curve = [m for m in metrics if m.get("curve_group") == "eur_yield_curve" and m.get("is_curve_tenor")]

    assert [m["metric_id"] for m in sorted(curve, key=lambda m: m["tenor_order"])] == [
        "eur_3m_yield",
        "eur_6m_yield",
        "eur_1y_yield",
        "eur_2y_yield",
        "eur_3y_yield",
        "eur_5y_yield",
        "eur_7y_yield",
        "eur_10y_yield",
        "eur_20y_yield",
        "eur_30y_yield",
    ]
    assert {m["metric_id"] for m in curve if m.get("highlight_on_curve")} == {
        "eur_2y_yield",
        "eur_5y_yield",
        "eur_10y_yield",
        "eur_30y_yield",
    }


def test_jgb_curve_supports_full_available_tenor_ladder():
    metrics = yaml.safe_load(Path("config/metrics_catalog.yml").read_text())["metrics"]
    curve = [m for m in metrics if m.get("curve_group") == "jp_jgb_curve" and m.get("is_curve_tenor")]

    assert [m["metric_id"] for m in sorted(curve, key=lambda m: m["tenor_order"])] == [
        "jgb_1y",
        "jgb_2y",
        "jgb_3y",
        "jgb_4y",
        "jgb_5y",
        "jgb_6y",
        "jgb_7y",
        "jgb_8y",
        "jgb_9y",
        "jgb_10y",
        "jgb_15y",
        "jgb_20y",
        "jgb_25y",
        "jgb_30y",
        "jgb_40y",
    ]
    assert {m["metric_id"] for m in curve if m.get("highlight_on_curve")} == {
        "jgb_2y",
        "jgb_5y",
        "jgb_10y",
        "jgb_30y",
    }
