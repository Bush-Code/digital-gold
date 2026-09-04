# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-09-05

### Added
- Streamlit dashboard (`main.py`) testing whether Bitcoin behaves as a safe
  haven, a diversifier or a risk asset.
- Binance public REST client with **pagination** across the venue's 1000-candle
  ceiling, so multi-year histories are not silently truncated.
- Frankfurter (ECB) FX client that inverts quotes to USD-per-unit, so a rising
  line always means a strengthening asset.
- Centralised HTTP layer with retry-on-transient and a single structured
  `ApiError` type surfaced to the UI.
- Trading-day intersection join, keeping only days every source actually quoted.
- Risk statistics: annualised return, annualised volatility, maximum drawdown.
- Safe-haven assessment after Baur & Lucey (2010), with stress defined by the
  currency basket alone so the test is not circular.
- Real gold (PAXG) as the comparison yardstick on the identical stressed subsample.
- Five Plotly views on a colour-vision-validated palette.
- 55 tests with mocked network calls (97% statement coverage).

### Fixed
- **Safe-haven classification no longer compares calm against stressed
  correlation.** Conditioning on the worst decile truncates the basket's range
  and attenuates correlation as a statistical artefact, which mislabelled a
  market-amplifying asset as a diversifier. Classification now scores the
  stressed correlation's level against a documented threshold. Covered by a
  regression test.
- Legend no longer overlaps the chart title in narrow side-by-side columns.

### Notes
- Targets Python 3.13 for Streamlit Community Cloud compatibility, though
  3.11–3.14 are supported.
- CoinGecko was evaluated and rejected: the public tier caps history at 365 days
  and returned HTTP 429 after two consecutive requests.
