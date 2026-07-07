"""FX transforms."""

from __future__ import annotations

import pandas as pd

from dashboard.transforms.returns import calculate_price_returns


def calculate_fx_returns(
    df: pd.DataFrame,
    as_of: str = "latest",
    add_usd_strength_adjusted: bool = True,
) -> pd.DataFrame:
    result = calculate_price_returns(df, as_of)
    if result.empty or not add_usd_strength_adjusted:
        return result
    for column in [col for col in result.columns if col.endswith("_return_pct")]:
        result[f"usd_strength_adjusted_{column}"] = result.apply(
            lambda row: -row[column] if str(row["metric_id"]).startswith("eur") else row[column],
            axis=1,
        )
    return result
