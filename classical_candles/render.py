"""Render a CandleSeries as a scrolling stock-chart video, then mux in the audio.

Performance note: a naive renderer would call `ax.cla()` and rebuild every
visible candle from scratch on every single video frame (thousands of times
for a multi-minute track), which is by far the slowest part of the whole
pipeline. Almost none of that work is actually necessary: within a candle's
own duration, every *completed* candle on screen is frozen -- only the one
candle currently forming changes shape from frame to frame.

So we split drawing into two tiers:
  - "static" layer: the axes, grid, and every completed candle in the
    current window. This is rebuilt only when a new candle completes
    (once every `candle_duration` seconds), then captured once as a bitmap.
  - "live" layer: the single in-progress candle, its wick, its volume bar,
    and the running price label. These are pre-created matplotlib artists
    that get their coordinates updated and blitted on top of the cached
    static bitmap on every frame -- no new objects, no full redraw.

Frames are streamed straight into an ffmpeg subprocess as raw RGBA bytes,
bypassing matplotlib's own (always-fully-redrawing) animation writer.
"""

from __future__ import annotations

import os
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
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
    body_width = candle_duration * 0.7
    min_body_h = None  # set once price range is known, below

    all_prices = np.array([v for c in candles for v in (c.high, c.low)])
    price_min, price_max = float(all_prices.min()), float(all_prices.max())
    pad = (price_max - price_min) * 0.08 or 1.0
    min_body_h = (price_max - price_min) * 0.0015

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

    ax.set_ylim(price_min - pad, price_max + pad)
    ax.set_ylabel("Price", color=FG, fontsize=9)
    ax_vol.set_ylim(0, 1.05)
    ax_vol.set_ylabel("Volume", color=FG, fontsize=9)
    ax_vol.set_xlabel("Time (s)", color=FG, fontsize=9)

    # ---- "live" artists: created once, repositioned every frame, never rebuilt ----
    live_body = Rectangle((0, 0), body_width, 0, facecolor=GREEN, edgecolor=GREEN, linewidth=0.5)
    live_wick = Line2D([0, 0], [0, 0], color=GREEN, linewidth=1.0, solid_capstyle="round")
    live_vol = Rectangle((0, 0), body_width, 0, facecolor=GREEN, edgecolor="none", alpha=0.6)
    price_label = ax.text(
        0.99, 1.02, "", transform=ax.transAxes, ha="right", va="bottom",
        color=FG, fontsize=11, fontweight="bold",
    )
    for artist in (live_body, live_wick, live_vol, price_label):
        artist.set_animated(True)
    ax.add_patch(live_body)
    ax.add_line(live_wick)
    ax_vol.add_patch(live_vol)

    # ---- "static" layer: rebuilt only when the completed-candle window changes ----
    static_artists = []
    background = [None]
    last_idx_end = [-1]

    def rebuild_static(idx_end: int) -> None:
        for artist in static_artists:
            artist.remove()
        static_artists.clear()

        idx_start = max(0, idx_end - visible_candles + 1)
        completed = candles[idx_start:idx_end]

        for c in completed:
            color = GREEN if c.close >= c.open else RED
            wick = Line2D([c.t_start + body_width / 2] * 2, [c.low, c.high],
                          color=color, linewidth=1.0, solid_capstyle="round")
            ax.add_line(wick)
            y0 = min(c.open, c.close)
            h = max(abs(c.close - c.open), min_body_h)
            body = Rectangle((c.t_start, y0), body_width, h, facecolor=color, edgecolor=color, linewidth=0.5)
            ax.add_patch(body)
            vol = Rectangle((c.t_start, 0), body_width, max(c.volume, 0.01), facecolor=color, edgecolor="none", alpha=0.6)
            ax_vol.add_patch(vol)
            static_artists.extend([wick, body, vol])

        anchor = completed[0] if completed else candles[idx_end]
        t0 = anchor.t_start
        t1 = candles[idx_end].t_end
        ax.set_xlim(t0, t1 + candle_duration * 2)
        ax_vol.set_xlim(t0, t1 + candle_duration * 2)
        ax.set_title(title, color=FG, fontsize=13, fontweight="bold", loc="left")

        fig.canvas.draw()  # animated artists (live_*, price_label) are skipped here
        background[0] = fig.canvas.copy_from_bbox(fig.bbox)

    def update_live(current_time: float) -> None:
        idx_end = min(int(current_time / candle_duration), len(candles) - 1)
        if idx_end != last_idx_end[0]:
            rebuild_static(idx_end)
            last_idx_end[0] = idx_end

        cur = candles[idx_end]
        frac = (current_time - cur.t_start) / candle_duration
        pc = _partial_candle(cur, frac)
        color = GREEN if pc.close >= pc.open else RED

        live_body.set_x(pc.t_start)
        live_body.set_y(min(pc.open, pc.close))
        live_body.set_height(max(abs(pc.close - pc.open), min_body_h))
        live_body.set_facecolor(color)
        live_body.set_edgecolor(color)

        live_wick.set_data([pc.t_start + body_width / 2] * 2, [pc.low, pc.high])
        live_wick.set_color(color)

        live_vol.set_x(pc.t_start)
        live_vol.set_height(max(pc.volume, 0.01))
        live_vol.set_facecolor(color)

        price_label.set_text(f"${pc.close:,.2f}")
        price_label.set_color(GREEN if pc.close >= series.start_price else RED)

    tmp_video = output_path + ".silent.mp4"
    w_px, h_px = fig.canvas.get_width_height()

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pixel_format", "rgba",
        "-video_size", f"{w_px}x{h_px}", "-framerate", str(fps),
        "-i", "-",
        "-an",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        tmp_video,
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    report(f"Rendering {n_frames} frames...")
    try:
        for i in range(n_frames):
            t = i / fps
            update_live(t)

            fig.canvas.restore_region(background[0])
            ax.draw_artist(live_body)
            ax.draw_artist(live_wick)
            ax_vol.draw_artist(live_vol)
            ax.draw_artist(price_label)
            fig.canvas.blit(fig.bbox)

            proc.stdin.write(fig.canvas.buffer_rgba())

            if progress and i % max(1, n_frames // 20) == 0:
                report(f"Rendering... {int(100 * i / n_frames)}%")
    finally:
        proc.stdin.close()
        stderr = proc.stderr.read()
        proc.wait()
        plt.close(fig)

    if proc.returncode != 0:
        sys.stderr.write(stderr.decode(errors="ignore"))
        raise RuntimeError("ffmpeg failed while encoding the chart animation. See output above.")

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
