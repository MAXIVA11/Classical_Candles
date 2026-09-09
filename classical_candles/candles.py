"""Map musical features into OHLCV candlestick data.

Real stocks aren't a smooth curve -- they're a *random walk with drift*:
mostly noise, tick to tick, with a bias that only becomes visible once it
accumulates over many bars. That's the actual model used here, not just a
figure of speech:

    return_for_this_candle = drift + volatility * random_normal()

  - `drift` is small and comes from the melody: a smoothed pitch trend plus
    a bit of carried-over momentum, so an ascending passage nudges the price
    up over time. It is deliberately kept weaker than the noise term --
    a real uptrend is still full of red candles along the way.
  - `volatility` (how big the random swings are allowed to be) comes from
    onset sharpness/density and trading volume: a fast, busy passage gets
    wide, jagged bars, a calm one gets small, quiet ones. It never hits
    exactly zero, so even an adagio still breathes.
  - Trading volume itself -- how many "market participants" are active --
    is loudness blended with note density: a wall of fast notes reads as a
    busy, liquid market the same way sheer loudness does.
  - Spectral brightness (centroid) adds extra, asymmetric wick length on
    top of that: bright, percussive transients read as a sudden intrabar
    spike or rejection, same as a real high/low that the close doesn't hold.
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

    # Smooth the pitch line itself before taking slopes from it. Raw
    # semitone-to-semitone jumps are jittery (vibrato, tracking noise); an
    # EMA of the pitch line gives a much steadier trend to react to, the
    # same way a real ticker reacts to a moving average, not tick noise.
    pitch_ema = pitch_filled.copy()
    ema_alpha = 0.35
    for b in range(1, n_bins):
        if np.isnan(pitch_ema[b]):
            pitch_ema[b] = pitch_ema[b - 1]
        elif not np.isnan(pitch_ema[b - 1]):
            pitch_ema[b] = ema_alpha * pitch_ema[b] + (1 - ema_alpha) * pitch_ema[b - 1]

    # "Volume" = how many market participants are trading. Loudness alone
    # isn't a great proxy (a single sustained loud note isn't busy trading),
    # so blend in note density: lots of attacks per second reads as a busy,
    # liquid market the same way loudness does.
    volume_by_bin = np.clip(0.55 * rms_by_bin + 0.45 * onset_density_by_bin, 0.0, 1.0)

    series = CandleSeries(start_price=start_price)
    price = start_price
    rng = np.random.default_rng(42)  # deterministic "market noise"
    momentum = 0.0

    for b in range(n_bins):
        open_p = price

        pitch_delta = 0.0
        if b > 0 and not np.isnan(pitch_ema[b]) and not np.isnan(pitch_ema[b - 1]):
            pitch_delta = pitch_ema[b] - pitch_ema[b - 1]

        sharpness = onset_by_bin[b]
        density = onset_density_by_bin[b]
        intensity = float(np.clip(0.5 * sharpness + 0.5 * density, 0.0, 1.0))
        volume = float(volume_by_bin[b])

        # Momentum carries part of the previous move forward -- a melodic
        # trend that's underway keeps nudging the drift for a few candles
        # instead of vanishing the instant the raw slope wobbles.
        trend_signal = 0.65 * pitch_delta + 0.35 * momentum
        momentum = 0.6 * momentum + 0.4 * pitch_delta

        # Drift: a gentle, musically-driven bias. Deliberately small --
        # this is what accumulates into a visible trend over many candles,
        # it should not by itself decide any single candle's color.
        drift = max_move_pct * 0.35 * np.clip(trend_signal / 3.0, -1.0, 1.0)

        # Volatility: how wide this candle's random swing is allowed to be.
        # Busy, sharp, well-traded passages get wide bars; quiet ones get
        # small ones, but never all the way down to zero -- a real market
        # never trades in a perfectly straight line.
        volatility = max_move_pct * (0.22 + 0.85 * intensity) * (0.45 + 0.55 * volume)

        # The random walk step itself. This is what actually makes it look
        # like a stock and not a smoothed curve: every candle gets its own
        # independent noise draw, so bar-to-bar size and direction jump
        # around even while the drift slowly leans the whole thing one way.
        shock = rng.standard_normal()
        raw_return = drift + volatility * shock
        body_pct_signed = float(np.clip(raw_return, -max_move_pct * 3.2, max_move_pct * 3.2))

        close_p = open_p * (1.0 + body_pct_signed)

        # Wicks: an intrabar excursion beyond the close, asymmetric like a
        # real bar (upper and lower shadows are rarely the same length).
        wick_base = (
            max_wick_pct
            * (0.2 + 0.8 * centroid_by_bin[b])
            * (0.3 + 0.7 * sharpness)
            * (0.5 + 0.5 * volume)
        )
        upper_wick_pct = wick_base * rng.uniform(0.4, 1.4)
        lower_wick_pct = wick_base * rng.uniform(0.4, 1.4)
        hi = max(open_p, close_p) * (1.0 + upper_wick_pct)
        lo = min(open_p, close_p) * (1.0 - lower_wick_pct)

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
