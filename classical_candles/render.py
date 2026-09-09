"""Render a CandleSeries as a scrolling stock-chart video, then mux in the audio."""

from __future__ import annotations

import os
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FFMpegWriter
from matplotlib.patches import Rectangle

from .candles import Candle, CandleSeries

GREEN = "#26a69a"
RED = "#ef5350"
BG = "#0d1117"
GRID = "#21262d"
FG = "#e6edf3"


def _partial_candle(c: Candle, elapsed_frac: float) -> Candle:
    """Interpolate a candle as if we're partway through forming it live."""
    elapsed_frac = float(np.clip(elapsed_frac, 0.0, 1.0))
    close = c.open + (c.close - c.open) * elapsed_frac
    hi = c.open + (c.high - c.open) * elapsed_frac if c.high >= c.open else c.high
    lo = c.open - (c.open - c.low) * elapsed_frac if c.low <= c.open else c.low
    hi = max(hi, c.open, close)
    lo = min(lo, c.open, close)
    return Candle(c.t_start, c.t_end, c.open, hi, lo, close, c.volume * elapsed_frac, c.intensity)


def render_video(
    series: CandleSeries,
    audio_path: str,
    output_path: str,
    title: str = "Classical Candles",
    fps: int = 30,
    visible_candles: int = 50,
    dpi: int = 120,
    width_px: int = 1280,
    height_px: int = 720,
    progress=None,
) -> str:
    """Render `series` as a scrolling candlestick chart video with audio."""

    def report(msg: str) -> None:
        if progress:
            progress(msg)

    candles = series.candles
    if not candles:
        raise ValueError("No candles to render.")

    duration = candles[-1].t_end
    n_frames = max(1, int(np.ceil(duration * fps)))
    candle_duration = candles[0].t_end - candles[0].t_start

    all_prices = np.array(
        [v for c in candles for v in (c.high, c.low)]
    )
    price_min, price_max = float(all_prices.min()), float(all_prices.max())
    pad = (price_max - price_min) * 0.08 or 1.0

    fig_w, fig_h = width_px / dpi, height_px / dpi
    fig, (ax, ax_vol) = plt.subplots(
        2, 1, figsize=(fig_w, fig_h), dpi=dpi,
        gridspec_kw={"height_ratios": [4, 1]}, sharex=False,
    )
    fig.patch.set_facecolor(BG)
    for a in (ax, ax_vol):
        a.set_facecolor(BG)
        a.tick_params(colors=FG, labelsize=8)
        for spine in a.spines.values():
            spine.set_color(GRID)
        a.grid(True, color=GRID, linewidth=0.6, alpha=0.7)

    ax.set_title(title, color=FG, fontsize=13, fontweight="bold", loc="left")
    price_label = ax.text(
        0.99, 1.02, "", transform=ax.transAxes, ha="right", va="bottom",
        color=FG, fontsize=11, fontweight="bold",
    )

    body_width = candle_duration * 0.7

    def draw_frame(current_time: float):
        ax.cla()
        ax_vol.cla()
        for a in (ax, ax_vol):
            a.set_facecolor(BG)
            a.tick_params(colors=FG, labelsize=8)
            for spine in a.spines.values():
                spine.set_color(GRID)
            a.grid(True, color=GRID, linewidth=0.6, alpha=0.7)

        idx_end = int(current_time / candle_duration)
        idx_end = min(idx_end, len(candles) - 1)
        idx_start = max(0, idx_end - visible_candles + 1)
        window = list(candles[idx_start:idx_end])

        cur = candles[idx_end]
        frac = (current_time - cur.t_start) / candle_duration
        window.append(_partial_candle(cur, frac))

        for c in window:
            color = GREEN if c.close >= c.open else RED
            ax.plot([c.t_start + body_width / 2] * 2, [c.low, c.high],
                    color=color, linewidth=1.0, solid_capstyle="round")
            y0 = min(c.open, c.close)
            h = max(abs(c.close - c.open), (price_max - price_min) * 0.0015)
            ax.add_patch(Rectangle(
                (c.t_start, y0), body_width, h,
                facecolor=color, edgecolor=color, linewidth=0.5,
            ))
            ax_vol.add_patch(Rectangle(
                (c.t_start, 0), body_width, max(c.volume, 0.01),
                facecolor=color, edgecolor="none", alpha=0.6,
            ))

        t0, t1 = window[0].t_start, window[-1].t_end
        ax.set_xlim(t0, t1 + candle_duration * 2)
        ax.set_ylim(price_min - pad, price_max + pad)
        ax.set_ylabel("Price", color=FG, fontsize=9)
        ax.set_title(title, color=FG, fontsize=13, fontweight="bold", loc="left")

        ax_vol.set_xlim(t0, t1 + candle_duration * 2)
        ax_vol.set_ylim(0, 1.05)
        ax_vol.set_ylabel("Volume", color=FG, fontsize=9)
        ax_vol.set_xlabel("Time (s)", color=FG, fontsize=9)

        price_label.set_text(f"${window[-1].close:,.2f}")
        price_label.set_color(GREEN if window[-1].close >= series.start_price else RED)

    tmp_video = output_path + ".silent.mp4"
    writer = FFMpegWriter(fps=fps, codec="libx264", bitrate=-1,
                           extra_args=["-pix_fmt", "yuv420p", "-crf", "18"])

    report(f"Rendering {n_frames} frames...")
    with writer.saving(fig, tmp_video, dpi=dpi):
        for i in range(n_frames):
            t = i / fps
            draw_frame(t)
            writer.grab_frame()
            if progress and i % max(1, n_frames // 20) == 0:
                report(f"Rendering... {int(100 * i / n_frames)}%")
    plt.close(fig)

    report("Muxing audio into video...")
    _mux_audio(tmp_video, audio_path, output_path, duration)
    os.remove(tmp_video)
    report(f"Done -> {output_path}")
    return output_path


def _mux_audio(video_path: str, audio_path: str, output_path: str, duration: float) -> None:
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-t", str(duration),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        sys.stderr.write(result.stdout.decode(errors="ignore"))
        raise RuntimeError("ffmpeg failed to mux audio and video. See output above.")
