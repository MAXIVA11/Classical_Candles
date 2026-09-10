"""Split one recording into "sectors" that each trade as their own stock.

True per-instrument separation (isolating "the violins" from "the cellos")
needs a trained source-separation model, and generic ones are built for
pop/rock stems (vocals/drums/bass/other) -- they don't do orchestral
instruments justice. Instead, this splits the mix by frequency register,
which tracks real orchestration surprisingly well: the bass/cello line
lives in the low band, inner voices and winds sit in the middle, and
violins/flutes dominate the top. It's an honest approximation, labeled as
such, not a claim of true instrument isolation.

Each sector gets its own onset/loudness/brightness analysis (fast -- no
pitch tracking) and its own independent random-walk noise, but all of them
lean on the *same* melodic drift computed once from the full mix -- the
same way real sector stocks move together on market-wide sentiment while
diverging on their own idiosyncratic volatility.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, sosfiltfilt

from .analysis import AudioFeatures, analyze_features
from .candles import CandleSeries, build_candles
from .ticker import Ticker, generate_ticker

# (key, display label, low Hz, high Hz, rng seed offset)
SECTOR_BANDS = [
    ("bass", "Bass & Cellos", 20, 250, 1),
    ("mid", "Winds & Violas", 250, 2000, 2),
    ("treble", "Violins & Flutes", 2000, 9000, 3),
]


@dataclass
class Sector:
    key: str
    label: str
    ticker: Ticker
    series: CandleSeries


def _bandpass(y: np.ndarray, sr: int, low: float, high: float) -> np.ndarray:
    nyq = sr / 2.0
    low_n = max(low / nyq, 1e-4)
    high_n = min(high / nyq, 0.999)
    sos = butter(4, [low_n, high_n], btype="band", output="sos")
    return sosfiltfilt(sos, y).astype(np.float32)


def build_sectors(
    y: np.ndarray,
    sr: int,
    main_features: AudioFeatures,
    title: str,
    candle_duration: float,
    max_move_pct: float,
    max_wick_pct: float,
    trend_signal: np.ndarray,
    main_symbol: str,
    progress=None,
) -> list[Sector]:
    """Build one correlated-but-distinct CandleSeries per frequency sector."""

    def report(msg: str) -> None:
        if progress:
            progress(msg)

    sectors = []
    for key, label, low, high, seed_offset in SECTOR_BANDS:
        report(f"Splitting out the {label.lower()}...")
        y_band = _bandpass(y, sr, low, high)

        band_features = analyze_features(y_band, sr, estimate_pitch=False)

        ticker = generate_ticker(f"{title} — {label}")
        # `_make_symbol` truncates to its first few significant words, so a
        # suffix appended to a long title rarely survives into the symbol.
        # Force each sector to a visibly distinct, still-related ticker.
        ticker.symbol = f"{main_symbol[:3]}{key[0].upper()}"

        series = build_candles(
            band_features,
            candle_duration=candle_duration,
            start_price=ticker.start_price,
            max_move_pct=max_move_pct,
            max_wick_pct=max_wick_pct,
            trend_signal=trend_signal,
            rng_seed=42 + seed_offset,
        )
        sectors.append(Sector(key=key, label=label, ticker=ticker, series=series))

    return sectors
