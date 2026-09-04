# 🪙 Digital Gold?

**Is Bitcoin a store of value, or a risk asset wearing gold's clothes?**

An interactive dashboard that tests the "digital gold" claim empirically, using
two independent public data sources and no API keys.

---

## The question

Bitcoin is routinely described as "digital gold" — an asset that holds its value
when markets fall. That is a testable claim, and this project tests it.

The finance literature (Baur & Lucey, 2010) draws a sharp distinction:

| Label | Definition |
|---|---|
| **Safe haven** | Uncorrelated or *negatively* correlated with risk assets **during market stress** |
| **Diversifier** | Weakly correlated on average, but offers no special protection in a crisis |
| **Risk asset** | Falls together with everything else, exactly when protection is needed |

The distinction matters: an asset that only diversifies in calm markets is not a
haven. So this project measures Bitcoin's behaviour **on the worst days only**,
and compares it against *actual, physical gold* on those very same days.

## Why this data

| Source | Provides | Auth | Why chosen |
|---|---|---|---|
| **Binance** public REST | Daily OHLCV for BTC, ETH, SOL, XRP and **PAXG** | None | Full history back to Aug 2017; no rate-limiting under normal use |
| **Frankfurter** (ECB) | Daily reference rates for CHF, JPY, AUD, EUR | None | Official European Central Bank rates; entire history in one request |

**PAXG is the key to the whole project.** It is a token redeemable for one troy
ounce of LBMA-accredited gold held in Brink's vaults. It gives us a real gold
price on the *same venue*, the *same clock* and the *same quote currency* as
Bitcoin — so "is Bitcoin like gold?" becomes a direct measurement rather than a
metaphor, with no cross-venue timestamp mismatch to explain away.

CHF and JPY are the textbook safe-haven currencies; AUD and EUR act as the risk
basket that defines what "market stress" means.

---

## Method

Three decisions do most of the analytical work:

**1. Join on genuinely shared trading days.**
Crypto trades 24/7; the ECB publishes only on business days. Forward-filling the
weekend would invent flat observations and drag every correlation toward zero, so
the panel keeps only days on which *every* selected source actually quoted a
price. The app tells you the resulting window, which can be shorter than the one
you picked — PAXG did not list until August 2020.

**2. Define stress without the asset under test.**
Stress days are the worst decile of the **currency basket**, never of Bitcoin
itself. Otherwise the test would be circular: an asset always correlates with its
own bad days.

**3. Judge the *level* of the stressed correlation, not the calm-vs-stress change.**
This one is subtle, and it is a genuine trap. Conditioning on the worst decile
truncates the range of the basket, and a correlation measured over a restricted
range is attenuated *purely as a statistical artefact*. Compare calm against
stressed and almost any asset — including one that amplifies the market — appears
to "decouple." The project therefore scores the stressed correlation against a
fixed threshold, and against gold measured on the identical subsample.

> A regression test (`test_amplifying_asset_is_not_mislabelled_despite_range_restriction`)
> pins this behaviour: a deliberately market-amplifying asset must still be
> labelled a risk asset even though its correlation attenuates under stress.

---

## What it shows

Five views, driven by a sidebar (date range, instruments, asset under test,
rolling window, stress threshold):

- **🎯 The test** — the asset's stress correlation beside real gold's, on the same days
- **📈 Performance** — every series indexed to 100, plus annualised return, volatility and max drawdown
- **🔗 Correlation** — a full correlation matrix and a rolling correlation that exposes regime change
- **⚖️ Risk & reward** — annualised return against volatility
- **🗂 Data** — the aligned panel, downloadable as CSV

### A sample finding

Over the four years to September 2026, Bitcoin's correlation with falling
currency markets was **+0.03**, against real gold's **−0.02**. Gold cleared the
safe-haven bar; Bitcoin sat just above it, as a *diversifier*. Bitcoin delivered a
far higher return over the period — at roughly **three times** gold's volatility
and a much deeper drawdown.

Change the window and the verdict can change. That instability is a finding in
itself, and the dashboard is built to let you see it rather than hide it.

### An honest limitation

The risk basket here is **currencies**, not equities. Bitcoin's much-discussed
correlation with tech stocks is therefore *not* what this measures — neither
source offers equity data without a key. What is measured is well defined:
behaviour during foreign-exchange stress.

---

## Running it

**Requirements:** Python 3.11–3.14 and [Poetry](https://python-poetry.org/docs/#installation).

```bash
git clone <this repository>
cd digital-gold
poetry install
poetry run streamlit run main.py
```

The app opens at `http://localhost:8501`. **The file to execute is `main.py`.**

No API keys, no accounts, no `.env` file — both upstream sources are public.

### Tests

```bash
poetry run pytest
```

55 tests cover the paging logic, the FX inversion, the trading-day join and the
safe-haven classification. Network calls are mocked, so the suite is offline and
deterministic.

---

## 🌐 Live app

**Streamlit link:** _pending deployment — see below._

To deploy: push to GitHub, then at [share.streamlit.io](https://share.streamlit.io)
point a new app at this repository with `main.py` as the entry point and Python
3.13. `poetry.lock` and `pyproject.toml` are committed, so dependencies resolve
automatically.

---

## Project layout

```
digital-gold/
├── main.py                        ← execute this
├── pyproject.toml / poetry.lock
├── src/digital_gold/
│   ├── config.py                  instruments and constants
│   ├── api/                       data access
│   │   ├── base.py                shared HTTP, retries, structured errors
│   │   ├── binance.py             paged OHLCV
│   │   └── frankfurter.py         ECB rates, inverted
│   ├── analysis/                  business logic
│   │   ├── metrics.py             joins, returns, volatility, drawdown
│   │   └── correlation.py         the safe-haven test
│   └── ui/charts.py               presentation
└── tests/                         55 tests
```

Data access, analysis and presentation are kept in separate layers: the analysis
modules take DataFrames and know nothing about HTTP or Streamlit, which is what
makes them straightforward to test.

### A note on the colour scheme

The palette is not chosen by eye. Every categorical set was run through a
colour-vision validator checking perceptual separation under protanopia,
deuteranopia and tritanopia, plus contrast against the dark background. That
constraint is why the scatter plot groups into exactly three families: no
four-colour set cleared the all-pairs threshold. There are no dual-axis charts
anywhere in this project.

---

## Authors

*(Add your names and email addresses here before submitting.)*

- Name — email
- Name — email

---

<sub>Built with **BUSH.AI** engineering standards. Data: Binance public API;
European Central Bank via Frankfurter. This project is an academic exercise in
data analysis and is **not** investment advice.</sub>
