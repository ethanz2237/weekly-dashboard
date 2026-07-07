import pandas as pd
import pytest

from dashboard.transforms.rates import (
    calculate_bps_changes,
    calculate_cross_market_yield_differentials,
    calculate_curve_spreads,
    calculate_hibor_sofr_spreads,
    calculate_us_rate_spreads,
)
from dashboard.transforms.fx import calculate_fx_returns
from dashboard.transforms.returns import calculate_price_returns


def test_price_return_calculation():
    df = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-06-24", "2026-07-01"],
            "metric_id": ["sp500", "sp500", "sp500"],
            "value": [100, 110, 121],
        }
    )

    result = calculate_price_returns(df, "2026-07-01")

    assert result.loc[0, "1W_return_pct"] == pytest.approx(10)
    assert result.loc[0, "YTD_return_pct"] == pytest.approx(21)


def test_bps_change_calculation():
    df = pd.DataFrame(
        {
            "date": ["2026-06-24", "2026-07-01"],
            "metric_id": ["us_10y_yield", "us_10y_yield"],
            "value": [4.0, 4.25],
        }
    )

    result = calculate_bps_changes(df, "2026-07-01")

    assert result.loc[0, "1W_change_bps"] == 25


def test_curve_spread_calculation():
    df = pd.DataFrame(
        {
            "date": ["2026-07-01", "2026-07-01"],
            "metric_id": ["us_2y_yield", "us_10y_yield"],
            "value": [4.0, 4.5],
        }
    )

    result = calculate_curve_spreads(df)

    assert result.loc[result["spread_id"] == "2s10s", "value"].iloc[0] == 50
    assert result.loc[result["spread_id"] == "2s10s", "metric_id"].iloc[0] == "us_2s10s"


def test_us_rate_spread_calculation():
    df = pd.DataFrame(
        {
            "date": ["2026-07-01", "2026-07-01", "2026-07-01"],
            "metric_id": ["sofr", "effr", "iorb"],
            "value": [4.10, 4.00, 4.15],
        }
    )

    result = calculate_us_rate_spreads(df)

    assert result.loc[result["metric_id"] == "sofr_minus_effr", "value"].iloc[0] == pytest.approx(10)
    assert result.loc[result["metric_id"] == "iorb_minus_effr", "value"].iloc[0] == pytest.approx(15)


def test_us_rate_spread_missing_source_does_not_crash():
    df = pd.DataFrame(
        {
            "date": ["2026-07-01"],
            "metric_id": ["sofr"],
            "value": [4.10],
        }
    )

    result = calculate_us_rate_spreads(df)

    assert result.empty


def test_fx_returns_respect_as_of():
    df = pd.DataFrame(
        {
            "date": ["2026-06-24", "2026-07-01", "2026-07-08"],
            "metric_id": ["eurusd", "eurusd", "eurusd"],
            "value": [1.0, 1.1, 2.0],
        }
    )

    result = calculate_fx_returns(df, "2026-07-01", add_usd_strength_adjusted=False)

    assert result.loc[0, "latest_level"] == pytest.approx(1.1)
    assert result.loc[0, "1W_return_pct"] == pytest.approx(10)


def test_hibor_sofr_spread_calculation():
    df = pd.DataFrame(
        {
            "date": ["2026-07-01", "2026-07-01"],
            "metric_id": ["hibor_3m", "sofr"],
            "value": [4.0, 3.5],
        }
    )

    result = calculate_hibor_sofr_spreads(df)

    assert result.loc[result["metric_id"] == "hibor_3m_minus_sofr", "value"].iloc[0] == pytest.approx(50)


def test_cross_market_yield_differential_uses_local_minus_usd():
    df = pd.DataFrame(
        {
            "date": ["2026-07-01", "2026-07-01"],
            "metric_id": ["eur_10y_yield", "us_10y_yield"],
            "value": [3.0, 4.25],
        }
    )

    result = calculate_cross_market_yield_differentials(df)

    assert result.loc[result["metric_id"] == "eurusd_10y_yield_diff", "value"].iloc[0] == pytest.approx(-125)
