"""Command-line interface for Classical Candles."""

from __future__ import annotations

import argparse
import os
import re
import sys


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", text)[:80] or "track"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="classical-candles",
        description="Turn a classical music track into a stock-market candlestick chart video.",
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="YouTube URL of the track to download.")
    src.add_argument("--input-audio", help="Path to a local audio file (skips download).")

    p.add_argument("--output", help="Output video path (default: output/<title>.mp4)")
    p.add_argument("--title", help="Override the chart title (default: video/file title).")
    p.add_argument("--candle-duration", type=float, default=0.4,
                    help="Seconds of audio per candle (default: 0.4). Smaller = more frantic chart.")
    p.add_argument("--visible-candles", type=int, default=50,
                    help="How many candles are visible on screen at once (default: 50).")
    p.add_argument("--fps", type=int, default=30, help="Video frame rate (default: 30).")
    p.add_argument("--start-price", type=float, default=100.0, help="Starting price (default: 100).")
    p.add_argument("--max-move-pct", type=float, default=0.045,
                    help="Max body size per candle as a fraction of price (default: 0.045).")
    p.add_argument("--max-wick-pct", type=float, default=0.02,
                    help="Max wick size per candle as a fraction of price (default: 0.02).")
    p.add_argument("--no-pitch", action="store_true",
                    help="Skip melody pitch tracking (faster, but direction is loudness-driven only).")
    p.add_argument("--cache-dir", default="cache", help="Where downloaded audio is cached.")
    p.add_argument("--keep-cache", action="store_true",
                    help="Keep the cached/downloaded audio file after rendering (default: keep).")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    from .downloader import download_audio
    from .analysis import analyze_audio
    from .candles import build_candles
    from .render import render_video

    def log(msg: str) -> None:
        print(f"[classical-candles] {msg}")

    if args.url:
        log(f"Fetching audio for: {args.url}")
        track = download_audio(args.url, cache_dir=args.cache_dir)
        audio_path, title = track.path, track.title
    else:
        audio_path = args.input_audio
        title = os.path.splitext(os.path.basename(audio_path))[0]

    if args.title:
        title = args.title

    output = args.output
    if not output:
        os.makedirs("output", exist_ok=True)
        output = os.path.join("output", f"{_slugify(title)}.mp4")

    log(f"Analyzing: {title}")
    features = analyze_audio(audio_path, estimate_pitch=not args.no_pitch, progress=log)

    log("Mapping music to candles...")
    series = build_candles(
        features,
        candle_duration=args.candle_duration,
        start_price=args.start_price,
        max_move_pct=args.max_move_pct,
        max_wick_pct=args.max_wick_pct,
    )
    log(f"Generated {len(series.candles)} candles over {features.duration:.1f}s.")

    render_video(
        series,
        audio_path=audio_path,
        output_path=output,
        title=title,
        fps=args.fps,
        visible_candles=args.visible_candles,
        progress=log,
    )

    final_close = series.candles[-1].close
    change_pct = 100 * (final_close - args.start_price) / args.start_price
    direction = "UP" if change_pct >= 0 else "DOWN"
    log(f"'{title}' closed at ${final_close:,.2f} ({direction} {change_pct:+.1f}%)")
    log(f"Video saved to: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
