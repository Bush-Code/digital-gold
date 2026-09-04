"""
================================================================================
  BUSH.AI  |  PROPRIETARY
--------------------------------------------------------------------------------
  Module      : digital_gold.config
  Identifier  : 7061fc89-e43a-4a7a-9dc2-b0a82af37341
  Created     : 2026-09-05
  Purpose     : Central, typed definitions of every asset and currency studied.
================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final


class AssetClass(str, Enum):
    """Economic family an instrument belongs to.

    The whole research question is whether CRYPTO behaves like PRECIOUS_METAL
    (a store of value) or like a risk asset, so the class is what we group by.
    """

    CRYPTO = "Crypto"
    PRECIOUS_METAL = "Precious Metal"
    SAFE_HAVEN_FX = "Safe-Haven Currency"
    RISK_FX = "Risk Currency"


@dataclass(frozen=True, slots=True)
class Instrument:
    """A single tradable series we pull, analyse and chart."""

    code: str
    label: str
    asset_class: AssetClass
    source: str

    @property
    def is_crypto_venue(self) -> bool:
        return self.source == "binance"


# --- Binance instruments -----------------------------------------------------
# PAXG is a token redeemable for one troy ounce of LBMA-accredited gold held in
# Brink's vaults. It gives us a real gold price on the same venue, same 24/7
# clock and same quote currency as BTC -- no cross-venue timestamp mismatch.
BINANCE_INSTRUMENTS: Final[tuple[Instrument, ...]] = (
    Instrument("BTCUSDT", "Bitcoin", AssetClass.CRYPTO, "binance"),
    Instrument("ETHUSDT", "Ethereum", AssetClass.CRYPTO, "binance"),
    Instrument("SOLUSDT", "Solana", AssetClass.CRYPTO, "binance"),
    Instrument("XRPUSDT", "XRP", AssetClass.CRYPTO, "binance"),
    Instrument("PAXGUSDT", "Gold (PAXG)", AssetClass.PRECIOUS_METAL, "binance"),
)

# --- Frankfurter (ECB reference rates) ---------------------------------------
# CHF and JPY are the textbook safe havens; AUD is the textbook risk proxy.
# If Bitcoin is "digital gold" it should lean with CHF/JPY, not with AUD.
FX_INSTRUMENTS: Final[tuple[Instrument, ...]] = (
    Instrument("CHF", "Swiss Franc", AssetClass.SAFE_HAVEN_FX, "frankfurter"),
    Instrument("JPY", "Japanese Yen", AssetClass.SAFE_HAVEN_FX, "frankfurter"),
    Instrument("AUD", "Australian Dollar", AssetClass.RISK_FX, "frankfurter"),
    Instrument("EUR", "Euro", AssetClass.RISK_FX, "frankfurter"),
)

ALL_INSTRUMENTS: Final[tuple[Instrument, ...]] = BINANCE_INSTRUMENTS + FX_INSTRUMENTS

BY_CODE: Final[dict[str, Instrument]] = {i.code: i for i in ALL_INSTRUMENTS}

BENCHMARK_CODE: Final[str] = "BTCUSDT"
GOLD_CODE: Final[str] = "PAXGUSDT"

# Binance served its first BTCUSDT daily candle in Aug 2017; anything earlier
# returns an empty list rather than an error, so we clamp requests here.
EARLIEST_DATE: Final[str] = "2017-08-17"

TRADING_DAYS_PER_YEAR: Final[int] = 252
