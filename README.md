∑# Weekly Financial Dashboard

## Project Purpose

This project builds a weekly financial dashboard from public and optional premium market data, then prepares outputs for charts, Markdown, JSON, and Notion publishing.

The current MVP fetches implemented FRED, yfinance, HKMA, and Treasury FiscalData metrics. Planned production metrics live in the catalog before their fetchers are wired in.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Environment Variables

Copy `.env.example` to `.env` and fill in the values you need:

```bash
cp .env.example .env
```

Optional providers can stay blank until a metric needs them.

Notion publishing uses the existing Weekly Dashboard database configured by `NOTION_TOKEN`, `NOTION_DATABASE_ID`, and, when available, `NOTION_DATA_SOURCE_ID`. The publisher creates a new page from `output/latest/dashboard.md` or `output/dashboard.md`;Notion publishing uses the existing Weekly Dashboard database configured by `NOTION_TOKEN`, `NOTION_DATABASE_ID`, and, when available, `NOTION_DATA_SOURCE_ID`. The publisher creates a new page from `output/latest/dashboard.md` or `output/latest/dashboard.json` and attempts to upload local chart images. If chart upload fails, it inserts chart filename fallback notes without breaking the publish run.

## OpenBB Setup Notes

OpenBB is optional right now. The project checks whether OpenBB imports and keeps the fetcher non-blocking, but the MVP does not depend on OpenBB routes yet. This avoids breaking the weekly build on local OpenBB settings, provider-extension changes, or credentials that are only needed for future metrics.

## FRED API Key Notes

FRED is the current MVP source for US rates, credit, and liquidity data. Request a key from FRED and set `FRED_API_KEY` in `.env`.

## Current MVP Sources

- FRED: US Treasury yields, money-market rates, ON RRP/repo usage, TGA, bank reserves, US IG OAS, and US HY OAS.
- yfinance: global equity indices, ETF-based factor/sector proxy inputs, and FX spot.
- HKMA official API: HIBOR tenors, HKMA Aggregate Balance, and computed HIBOR-SOFR proxy spreads.
- Treasury FiscalData: recent auction results, bid-to-cover, bidder allocation shares, and an auction issuance proxy.
- ECB Data Portal: euro short-term rate, ECB policy rates, and the EUR yield curve tenor ladder.
- Japan MOF: constant-maturity JGB yield curve tenor ladder.
- OpenBB: optional import check only; no required MVP fetch path yet.

## HKMA Setup Notes

HKMA data uses official public APIs and requires no API key. Implemented HK rates currently include the populated tenors exposed by the HKMA HIBOR fixing feed: O/N, 1W, 1M, 3M, 6M, and 12M HIBOR, plus HKMA Aggregate Balance. HIBOR-SOFR spreads are MVP proxy spreads calculated as same-date HIBOR minus daily SOFR in basis points; they are not matched-tenor HKD/USD OIS spreads.

## Command Examples

```bash
python -m dashboard.run --as-of latest --mode build
python -m dashboard.run --as-of latest --mode validate-sources
python -m dashboard.run --mode source-health
python -m dashboard.run --mode pre-notion-check
python -m dashboard.run --mode check-env
python -m dashboard.run --as-of latest --mode publish-notion
```

## Source Resilience

Official API calls use retry with short exponential backoff for rate limits, 5xx errors, timeouts, and connection resets. If a live source fails, the build tries the last raw per-metric cache before marking an implemented metric missing.

Freshness thresholds are intentionally simple: daily market data uses 10 calendar days, weekly liquidity data uses 14 calendar days, and Treasury auction data uses 60 calendar days. Cache fallback rows are tagged as `cache_fallback` and reported separately in `output/source_validation_report.md`.

Secrets are sanitized before they reach validation reports, dashboard files, or console output. Query values such as `api_key` and environment values ending in `_KEY`, `_TOKEN`, or `_SECRET` are masked.

To check source health without a full dashboard build:

```bash
python -m dashboard.run --mode source-health
```

To clear cached fallback data, remove the raw cache directory:

```bash
rm -rf data/raw/metric_cache
```

## Chart Notes

Charts are saved as PNG files. Line and curve charts annotate latest values by default; heatmaps intentionally remain unannotated to avoid clutter.

Equity factor and sector views are lightweight ETF proxies. Growth vs value uses IWF/IWD, defensives vs cyclicals uses defensive sector ETFs divided by cyclical sector ETFs, and the US sector heatmap uses Select Sector SPDR ETF returns.

US money-market and liquidity views use FRED-hosted series, including NY Fed-origin repo/RRP operation data. SOFR-EFFR, IORB-EFFR, and UST curve spreads are computed internally from same-date source observations. The 3M Treasury minus OIS placeholder remains unimplemented until a free OIS source is added.

Treasury auction data uses the official FiscalData `auctions_query` endpoint and requires no API key. Bid-to-cover and bidder allocation shares are parsed from completed auctions across bills, notes, bonds, FRNs, and TIPS. Auction tail / stop-through remains a placeholder because a true calculation needs when-issued yield, which FiscalData does not provide.

EU rates use ECB Data Portal CSV endpoints and require no API key. The EUR curve uses the available ECB euro area yield curve ladder from 3M through 30Y and highlights 2Y, 5Y, 10Y, and 30Y. EU HY OAS uses FRED's ICE BofA Euro High Yield OAS series; EU IG OAS remains planned until a stable free source is verified.

Japan rates use the official Ministry of Finance JGB interest-rate CSV and require no API key. The JGB curve uses the available 1Y through 40Y ladder and highlights 2Y, 5Y, 10Y, and 30Y. BOJ policy pricing and JPY OIS remain planned until stable free sources are added.

China rates do not use brittle scraping. Planned CGB, DR007/FR007, LPR, MLF, and SLF metrics can be supplied through `data/manual/china_rates.csv` once source observations are available. The schema is:

```csv
date,metric_id,value,source,provider,notes
2026-07-01,cgb_10y,2.25,manual_csv,manual_china,example
```

Only use real observed values. If the file is empty or unavailable, China charts are skipped and the metrics remain planned rather than invented.

Cross-market yield differentials are computed only when both legs exist. The sign convention is local yield minus USD yield, reported in basis points; for example EURUSD 10Y is EUR 10Y yield minus US 10Y Treasury yield.

## Curve Data Policy

Curve charts should use the full available public tenor ladder where practical. Highlighted tenors are labels or visual emphasis points, not limits on what gets fetched. Derived spreads such as US 2s10s, 5s30s, and 10s30s are calculated from curve tenor series. Some markets may only have partial free/public curve data, so missing tenors should be reported instead of invented.

## Metrics Catalog

`config/metrics_catalog.yml` is the production-style source of truth for planned dashboard coverage. Every metric has source metadata, grouping, transform hints, chart hints, and two important control flags:

- `implemented: true` means the MVP pipeline currently knows how to fetch or produce the metric.
- `implemented: false` means the metric is planned but should not be treated as a missing data error yet.
- `premium_required: true` means the metric likely needs a paid or restricted dataset. These metrics are reported separately and must not fail the build.
- `deprecated: true` may be used for temporary backward compatibility, but deprecated metrics are kept out of the main planned/premium validation groups.

Validation separates implemented-present, implemented-missing, planned-not-implemented, premium-required, and deprecated metrics.

## How To Add A Metric

Add a new item to `config/metrics_catalog.yml` with all required fields:

- `metric_id`
- `display_name`
- `asset_class`
- `region`
- `group`
- `source`
- `provider`
- `ticker_or_series`
- `frequency`
- `unit`
- `transform`
- `chart_type`
- `fallback_source`
- `premium_required`
- `implemented`
- `notes`

Use bps changes for yields, rates, and spreads. Use percentage returns for equity, FX, and price-like data. Add planned metrics with `implemented: false` until a fetcher, transform, chart, and tests are ready. If a metric is optional or premium-only, set `premium_required: true` and keep missing data non-fatal.

## Development Roadmap

- Validate configuration files.
- Add source adapters without real dashboard coupling.
- Save raw and processed data snapshots.
- Build transforms for rates, spreads, FX, and equities.
- Generate PNG charts.
- Publish dashboard sections to Notion.
- Add graceful degradation for optional and missing metrics.
