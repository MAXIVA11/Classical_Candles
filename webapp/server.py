"""Local web app for Classical Candles.

Run with:

    python webapp/server.py

Then open http://127.0.0.1:5000 and paste a YouTube URL. Everything else
(download, analysis, ticker, candle math) happens automatically -- there is
exactly one input on the page.

The chart itself is never pre-rendered to video. The backend only has to
download the audio and crunch the musical features into candle data (a few
seconds of work); the browser then draws the candlestick chart live, frame
by frame, in perfect sync with the actual <audio> element as it plays. An
optional "save as video" pass is still available on demand for anyone who
wants an MP4 file to share.

Each listing also splits into three frequency-band "sectors" (bass, mid,
treble) that trade as their own correlated-but-distinct tickers, and a
live market-wire of headlines generated from whichever sector moves most.
"""

from __future__ import annotations

import mimetypes
import os
import re
import sys
import threading
import uuid

from flask import Flask, jsonify, request, send_from_directory, send_file

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classical_candles.downloader import download_audio
from classical_candles.analysis import analyze_features
from classical_candles.auto_params import derive_auto_params
from classical_candles.candles import build_candles, compute_trend_signal
from classical_candles.sectors import build_sectors
from classical_candles.news import generate_headlines
from classical_candles.ticker import generate_ticker
from classical_candles.render import render_video

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__, static_folder="static", static_url_path="")

JOBS: dict = {}
JOBS_LOCK = threading.Lock()

YOUTUBE_RE = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|m\.youtube\.com/watch\?v=)[\w\-]+"
)


def _new_job() -> str:
    job_id = uuid.uuid4().hex[:12]
    with JOBS_LOCK:
        JOBS[job_id] = {
            "status": "queued",
            "percent": 0,
            "log": [],
            "result": None,
            "error": None,
            "audio_path": None,
            "series": None,
            "video": {"status": "idle", "percent": 0, "video_url": None, "error": None},
        }
    return job_id


def _update(job_id: str, message: str = None, percent: int = None, status: str = None) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
        if message is not None:
            job["log"].append(message)
        if percent is not None:
            job["percent"] = percent
        if status is not None:
            job["status"] = status


def _candle_payload(series) -> list:
    return [
        [round(c.t_start, 3), round(c.open, 4), round(c.high, 4), round(c.low, 4), round(c.close, 4), round(c.volume, 4)]
        for c in series.candles
    ]


def _sector_summary(sector) -> dict:
    series = sector.series
    closes = [c.close for c in series.candles]
    highs = [c.high for c in series.candles]
    lows = [c.low for c in series.candles]
    final_close = closes[-1]
    change_pct = 100 * (final_close - series.start_price) / series.start_price
    return {
        "key": sector.key,
        "label": sector.label,
        "symbol": sector.ticker.symbol,
        "open": round(series.start_price, 2),
        "close": round(final_close, 2),
        "high": round(max(highs), 2),
        "low": round(min(lows), 2),
        "change_pct": round(change_pct, 2),
        "candles": _candle_payload(series),
    }


def _run_job(job_id: str, url: str) -> None:
    try:
        _update(job_id, "Cueing up the recording...", 5, "running")
        track = download_audio(url, cache_dir=CACHE_DIR)
        with JOBS_LOCK:
            JOBS[job_id]["audio_path"] = track.path

        _update(job_id, f"'{track.title}' is on the stand.", 12)
        ticker = generate_ticker(track.title)
        _update(job_id, f"Listed as {ticker.symbol} on the {ticker.exchange}.", 16)

        import librosa
        _update(job_id, "Loading audio...", None)
        y, sr = librosa.load(track.path, sr=22050, mono=True)

        def analysis_progress(msg: str) -> None:
            _update(job_id, msg, None)

        features = analyze_features(y, sr, estimate_pitch=True, progress=analysis_progress)
        _update(job_id, f"Tempo read at {features.tempo:.0f} BPM.", 60)

        params = derive_auto_params(features, ticker)
        trend_signal = compute_trend_signal(features, params.candle_duration)

        _update(job_id, "Translating the score into ticks...", 66)
        series = build_candles(
            features,
            candle_duration=params.candle_duration,
            start_price=params.start_price,
            max_move_pct=params.max_move_pct,
            max_wick_pct=params.max_wick_pct,
            trend_signal=trend_signal,
            rng_seed=42,
        )
        _update(job_id, f"{len(series.candles)} candles printed.", 72)

        def sector_progress(msg: str) -> None:
            _update(job_id, msg, None)

        sectors = build_sectors(
            y, sr, features, track.title,
            candle_duration=params.candle_duration,
            max_move_pct=params.max_move_pct,
            max_wick_pct=params.max_wick_pct,
            trend_signal=trend_signal,
            main_symbol=ticker.symbol,
            progress=sector_progress,
        )
        _update(job_id, "Sector desks are open.", 92)

        headlines = generate_headlines(
            sources=[("index", f"the {ticker.symbol} Index", series)]
            + [(s.key, s.label, s.series) for s in sectors],
            candle_duration=params.candle_duration,
        )
        _update(job_id, f"{len(headlines)} wire headlines queued.", 96)

        closes = [c.close for c in series.candles]
        highs = [c.high for c in series.candles]
        lows = [c.low for c in series.candles]
        volumes = [c.volume for c in series.candles]
        final_close = closes[-1]
        change_pct = 100 * (final_close - series.start_price) / series.start_price

        result = {
            "symbol": ticker.symbol,
            "exchange": ticker.exchange,
            "issuer": ticker.issuer,
            "open": round(series.start_price, 2),
            "close": round(final_close, 2),
            "high": round(max(highs), 2),
            "low": round(min(lows), 2),
            "change_pct": round(change_pct, 2),
            "volume": int(sum(volumes) * 1_000_000),
            "tempo": round(features.tempo, 1),
            "duration": round(features.duration, 1),
            "candle_duration": round(params.candle_duration, 4),
            "candles": _candle_payload(series),
            "sectors": [_sector_summary(s) for s in sectors],
            "headlines": [
                {"t": round(h.t, 3), "text": h.text, "direction": h.direction, "source": h.source}
                for h in headlines
            ],
            "audio_url": f"/media/{job_id}/audio",
            "title": f"{ticker.symbol} · {track.title}",
        }

        with JOBS_LOCK:
            JOBS[job_id]["series"] = series
            JOBS[job_id]["ticker_title"] = result["title"]

        _update(job_id, "Market is open.", 100, "done")
        with JOBS_LOCK:
            JOBS[job_id]["result"] = result

    except Exception as exc:  # noqa: BLE001
        _update(job_id, f"The exchange halted trading: {exc}", None, "error")
        with JOBS_LOCK:
            JOBS[job_id]["error"] = str(exc)


def _run_video_job(job_id: str) -> None:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        series = job["series"] if job else None
        audio_path = job["audio_path"] if job else None
        title = job.get("ticker_title", "Classical Candles") if job else "Classical Candles"

    def vupdate(percent=None, status=None, error=None):
        with JOBS_LOCK:
            v = JOBS[job_id]["video"]
            if percent is not None:
                v["percent"] = percent
            if status is not None:
                v["status"] = status
            if error is not None:
                v["error"] = error

    try:
        vupdate(percent=1, status="rendering")
        output_path = os.path.join(OUTPUT_DIR, f"{job_id}.mp4")

        def render_progress(msg: str) -> None:
            m = re.search(r"(\d+)%", msg)
            if m:
                vupdate(percent=min(int(m.group(1)), 99))

        render_video(
            series,
            audio_path=audio_path,
            output_path=output_path,
            title=title,
            fps=30,
            visible_candles=max(45, min(60, len(series.candles))),
            progress=render_progress,
        )
        with JOBS_LOCK:
            JOBS[job_id]["video"]["video_url"] = f"/media/{job_id}/video"
        vupdate(percent=100, status="done")
    except Exception as exc:  # noqa: BLE001
        vupdate(status="error", error=str(exc))


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/jobs", methods=["POST"])
def create_job():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not url:
        return jsonify({"error": "Paste a YouTube link first."}), 400
    if not YOUTUBE_RE.match(url):
        return jsonify({"error": "That doesn't look like a YouTube link."}), 400

    job_id = _new_job()
    thread = threading.Thread(target=_run_job, args=(job_id, url), daemon=True)
    thread.start()
    return jsonify({"job_id": job_id})


@app.route("/api/jobs/<job_id>")
def job_status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return jsonify({"error": "Unknown job."}), 404
        public = {k: v for k, v in job.items() if k not in ("series", "audio_path")}
        return jsonify(public)


@app.route("/api/jobs/<job_id>/video", methods=["POST"])
def start_video(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None or job.get("series") is None:
            return jsonify({"error": "That listing isn't ready yet."}), 400
        if job["video"]["status"] == "rendering":
            return jsonify({"status": "rendering"})
        if job["video"]["status"] == "done":
            return jsonify(job["video"])

    thread = threading.Thread(target=_run_video_job, args=(job_id,), daemon=True)
    thread.start()
    return jsonify({"status": "rendering"})


@app.route("/api/jobs/<job_id>/video")
def video_status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job is None:
            return jsonify({"error": "Unknown job."}), 404
        return jsonify(job["video"])


@app.route("/media/<job_id>/audio")
def media_audio(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        path = job["audio_path"] if job else None
    if not path or not os.path.exists(path):
        return jsonify({"error": "Audio not found."}), 404
    mime = mimetypes.guess_type(path)[0] or "audio/wav"
    return send_file(path, mimetype=mime, conditional=True)


@app.route("/media/<job_id>/video")
def media_video(job_id: str):
    path = os.path.join(OUTPUT_DIR, f"{job_id}.mp4")
    if not os.path.exists(path):
        return jsonify({"error": "Video not found."}), 404
    return send_file(path, mimetype="video/mp4", conditional=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Classical Candles is open for trading at http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
