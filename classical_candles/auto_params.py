"""Choose candle-rendering parameters automatically from the music itself.

The website exposes exactly one input to the user: a YouTube URL. Everything
else -- how long each candle lasts, how many are visible at once, how wild
the price swings get -- is derived from the track so a slow adagio and a
frantic presto each get a chart that suits them.
"""

from __future__ import annotations

from dataclasses import dataclass

from .analysis import AudioFeatures
from .ticker import Ticker


@dataclass
class AutoParams:
    candle_duration: float
    visible_candles: int
    max_move_pct: float
    max_wick_pct: float
    start_price: float


def derive_auto_params(features: AudioFeatures, ticker: Ticker) -> AutoParams:
    tempo = features.tempo if features.tempo and features.tempo > 1 else 90.0

    # One candle per roughly half a beat, clamped to a sane, watchable range.
    candle_duration = 30.0 / tempo
    candle_duration = min(max(candle_duration, 0.18), 0.55)

    # Longer pieces need a wider visible window so the chart doesn't feel
    # like it's crawling forever at the same zoom level.
    visible_candles = 60 if features.duration > 120 else 45

    return AutoParams(
        candle_duration=candle_duration,
        visible_candles=visible_candles,
        max_move_pct=0.045,
        max_wick_pct=0.02,
        start_price=ticker.start_price,
    )
