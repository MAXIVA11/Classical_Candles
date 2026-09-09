"""Map musical features into OHLCV candlestick data.

The mapping (the heart of "Classical Candles"):

  - Melody direction (pitch rising vs falling between bins) decides whether
    the candle is bullish (green, close > open) or bearish (red, close < open).
  - Onset strength + onset density (how sharp AND how frequent the note
    attacks are -- think a fast, sharply bowed violin run) drive how big the
    candle body is. Sharp + fast passages => big, fast price moves.
  - Spectral brightness (centroid) drives wick length -- bright, percussive
    transients create long wicks, like a sudden spike/rejection in price.
  - Loudness (RMS) becomes the volume bar under each candle.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .analysis import AudioFeatures


@dataclass
class Candle:
    t_start: float
    t_end: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    intensity: float  # 0..1, how "sharp & fast" this bin was (for visuals)


@dataclass
class CandleSeries:
    candles: list = field(default_factory=list)
    start_price: float = 100.0


def _minmax_norm(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    lo, hi = np.nanpercentile(x, 5), np.nanpercentile(x, 95)
    if hi - lo < 1e-9:
        return np.zeros_like(x)
    return np.clip((x - lo) / (hi - lo), 0.0, 1.0)


def build_candles(
    features: AudioFeatures,
    candle_duration: float = 0.4,
    start_price: float = 100.0,
    max_move_pct: float = 0.045,
    max_wick_pct: float = 0.02,
) -> CandleSeries:
    """Bin frame-level audio features into a sequence of OHLCV candles."""

    n_bins = max(1, int(np.ceil(features.duration / candle_duration)))
    bin_edges = np.arange(n_bins + 1) * candle_duration
    bin_idx = np.clip(
        np.digitize(features.frame_times, bin_edges) - 1, 0, n_bins - 1
    )

    onset_norm = _minmax_norm(features.onset_env)
    rms_norm = _minmax_norm(features.rms)
    centroid_norm = _minmax_norm(features.centroid)

    onset_by_bin = np.zeros(n_bins)
    onset_density_by_bin = np.zeros(n_bins)
    rms_by_bin = np.zeros(n_bins)
    centroid_by_bin = np.zeros(n_bins)
    pitch_by_bin = np.full(n_bins, np.nan)

    # A frame counts as a "sharp attack" if its onset strength stands out
    # locally -- this approximates fast note runs (many attacks per second).
    attack_threshold = np.nanpercentile(onset_norm, 70)

    for b in range(n_bins):
        mask = bin_idx == b
        if not np.any(mask):
            continue
        onset_by_bin[b] = float(np.mean(onset_norm[mask]))
        onset_density_by_bin[b] = float(np.mean(onset_norm[mask] > attack_threshold))
        rms_by_bin[b] = float(np.mean(rms_norm[mask]))
        centroid_by_bin[b] = float(np.mean(centroid_norm[mask]))
        pitches = features.pitch_hz[mask]
        voiced = pitches[~np.isnan(pitches)]
        if len(voiced) > 0:
            pitch_by_bin[b] = float(np.mean(12.0 * np.log2(voiced / 440.0)))

    # Fill unvoiced bins with the previous known pitch so direction can
    # still be inferred smoothly across silences/percussive passages.
    last = np.nan
    pitch_filled = pitch_by_bin.copy()
    for b in range(n_bins):
        if np.isnan(pitch_filled[b]):
            pitch_filled[b] = last
        else:
            last = pitch_filled[b]

    series = CandleSeries(start_price=start_price)
    price = start_price
    rng = np.random.default_rng(42)  # deterministic "market noise"

    for b in range(n_bins):
        open_p = price

        pitch_delta = 0.0
        if b > 0 and not np.isnan(pitch_filled[b]) and not np.isnan(pitch_filled[b - 1]):
            pitch_delta = pitch_filled[b] - pitch_filled[b - 1]

        sharpness = onset_by_bin[b]
        density = onset_density_by_bin[b]
        intensity = float(np.clip(0.5 * sharpness + 0.5 * density, 0.0, 1.0))

        if abs(pitch_delta) > 0.05:
            direction = 1.0 if pitch_delta > 0 else -1.0
            direction_strength = min(abs(pitch_delta) / 6.0, 1.0)  # ~half octave = max
        else:
            # No clear melodic direction (e.g. sustained/percussive/silent):
            # let loudness swings + a little deterministic noise decide it.
            drift = rms_by_bin[b] - (rms_by_bin[b - 1] if b > 0 else rms_by_bin[b])
            direction = 1.0 if (drift + rng.normal(0, 0.05)) >= 0 else -1.0
            direction_strength = 0.3

        body_pct = max_move_pct * (0.15 + 0.85 * intensity) * (0.4 + 0.6 * direction_strength)
        close_p = open_p * (1.0 + direction * body_pct)

        wick_pct = max_wick_pct * (0.2 + 0.8 * centroid_by_bin[b]) * (0.3 + 0.7 * sharpness)
        hi = max(open_p, close_p) * (1.0 + wick_pct)
        lo = min(open_p, close_p) * (1.0 - wick_pct)

        volume = rms_by_bin[b]

        series.candles.append(
            Candle(
                t_start=b * candle_duration,
                t_end=(b + 1) * candle_duration,
                open=open_p,
                high=hi,
                low=lo,
                close=close_p,
                volume=volume,
                intensity=intensity,
            )
        )
        price = close_p

    return series
