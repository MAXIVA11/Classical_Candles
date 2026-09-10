"""Turn an audio file into a stream of musical 'features' over time.

For every short frame of audio we measure:
  - loudness (RMS energy)                -> how big the trade volume is
  - onset strength (how sharp an attack is, e.g. a bowed violin note) -> volatility
  - spectral centroid (brightness/timbre) -> wick length
  - fundamental pitch (melody note)       -> whether the market goes up or down

These frame-level features are later grouped into fixed-size time bins,
one bin per candle, by candles.py.

`analyze_audio` loads a file and delegates to `analyze_features`, which
works on an in-memory waveform. Sector splitting (sectors.py) calls
`analyze_features` directly on band-filtered copies of the same waveform,
so a multi-sector listing only ever loads the file and estimates pitch
once, on the full mix -- the slow part of the pipeline doesn't multiply
per sector.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class AudioFeatures:
    sr: int
    hop_length: int
    frame_times: np.ndarray      # seconds, one per frame
    rms: np.ndarray              # loudness, one per frame
    onset_env: np.ndarray        # onset strength envelope, one per frame
    centroid: np.ndarray         # spectral centroid (Hz), one per frame
    pitch_hz: np.ndarray         # estimated fundamental pitch (NaN if unvoiced)
    duration: float              # seconds
    tempo: float                 # estimated tempo in BPM


def analyze_features(y: np.ndarray, sr: int, hop_length: int = 512,
                      estimate_pitch: bool = True, progress=None) -> "AudioFeatures":
    """Extract per-frame musical features from an already-loaded waveform."""
    import librosa

    def report(msg: str) -> None:
        if progress:
            progress(msg)

    duration = librosa.get_duration(y=y, sr=sr)

    report("Measuring loudness (RMS)...")
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

    report("Detecting note onsets (attack sharpness)...")
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)

    report("Measuring spectral brightness...")
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]

    report("Estimating tempo...")
    try:
        tempo_arr = librosa.feature.tempo(onset_envelope=onset_env, sr=sr, hop_length=hop_length)
    except AttributeError:
        tempo_arr = librosa.beat.tempo(onset_envelope=onset_env, sr=sr, hop_length=hop_length)
    tempo = float(tempo_arr[0]) if len(tempo_arr) else 90.0

    n_frames = min(len(rms), len(onset_env), len(centroid))

    if estimate_pitch:
        report("Tracking melody pitch (this can take a little while)...")
        f0, _voiced_flag, voiced_prob = librosa.pyin(
            y,
            fmin=librosa.note_to_hz("C2"),
            fmax=librosa.note_to_hz("C7"),
            sr=sr,
            hop_length=hop_length,
        )
        f0 = np.nan_to_num(f0, nan=np.nan)
        n_frames = min(n_frames, len(f0))
    else:
        f0 = np.full(n_frames, np.nan)

    frame_times = librosa.frames_to_time(
        np.arange(n_frames), sr=sr, hop_length=hop_length
    )

    return AudioFeatures(
        sr=sr,
        hop_length=hop_length,
        frame_times=frame_times,
        rms=rms[:n_frames],
        onset_env=onset_env[:n_frames],
        centroid=centroid[:n_frames],
        pitch_hz=f0[:n_frames],
        duration=float(duration),
        tempo=tempo,
    )


def analyze_audio(path: str, hop_length: int = 512, sr: int = 22050,
                   estimate_pitch: bool = True, progress=None) -> AudioFeatures:
    """Load an audio file and extract per-frame musical features from it.

    `progress` is an optional callable(str) used to report status.
    """
    import librosa

    if progress:
        progress("Loading audio...")
    y, loaded_sr = librosa.load(path, sr=sr, mono=True)
    return analyze_features(y, loaded_sr, hop_length=hop_length,
                             estimate_pitch=estimate_pitch, progress=progress)
