"""Download audio from a YouTube URL (or accept a local file) using yt-dlp."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass


@dataclass
class Track:
    path: str
    title: str


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", text)[:80] or "track"


def download_audio(url: str, cache_dir: str) -> Track:
    """Download the best audio stream for `url` and convert it to WAV.

    Returns the path to the extracted .wav file plus the video title.
    Cached: if a file for this URL's video id already exists, it is reused.
    """
    import yt_dlp

    os.makedirs(cache_dir, exist_ok=True)

    info_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(info_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    video_id = info.get("id", "audio")
    title = info.get("title", video_id)
    slug = _slugify(title)
    out_wav = os.path.join(cache_dir, f"{video_id}_{slug}.wav")

    if os.path.exists(out_wav):
        return Track(path=out_wav, title=title)

    out_template = os.path.join(cache_dir, f"{video_id}_{slug}.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "quiet": False,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    if not os.path.exists(out_wav):
        raise FileNotFoundError(
            f"Expected extracted audio at {out_wav}, but it was not created."
        )

    return Track(path=out_wav, title=title)
