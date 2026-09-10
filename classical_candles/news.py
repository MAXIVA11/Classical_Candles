"""Generate a live "market wire" of headlines from the biggest moves.

Every candle across the index and its sectors has a return; the ones that
stand out get turned into a wire headline, timestamped to when they happen
so the frontend can surface them as the track actually plays -- a live news
crawl reacting to the music, not a static summary.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .candles import CandleSeries

UP_TEMPLATES = [
    "{name} rallies {pct}",
    "Buyers pile into {name}",
    "{name} breaks out on heavy volume",
    "{name} surges as bulls take control",
    "Circuit-breaker watch as {name} melts up",
]
DOWN_TEMPLATES = [
    "{name} sells off {pct}",
    "{name} slides as sellers take control",
    "Panic hits {name}",
    "{name} tumbles on heavy volume",
    "Profit-taking knocks {name} down {pct}",
]


@dataclass
class Headline:
    t: float
    text: str
    direction: str  # "up" | "down"
    source: str


def generate_headlines(
    sources: list[tuple[str, str, CandleSeries]],
    candle_duration: float,
    max_headlines: int = 40,
    cooldown_seconds: float = 3.5,
) -> list[Headline]:
    """Build a chronological list of headlines from a set of named series.

    `sources` is a list of (key, display_name, series) tuples -- typically
    the index plus each sector. The series must all share the same candle
    timeline (same candle_duration, same bin count).
    """
    candidates = []
    for key, name, series in sources:
        for i, c in enumerate(series.candles):
            ret = (c.close - c.open) / c.open if c.open else 0.0
            candidates.append((abs(ret), ret, i, key, name))

    candidates.sort(key=lambda row: row[0], reverse=True)

    chosen: list[Headline] = []
    taken_times: list[float] = []
    rng = np.random.default_rng(7)

    for _, ret, i, key, name in candidates:
        if abs(ret) < 0.006:  # not interesting enough to report
            continue
        t = i * candle_duration
        if any(abs(t - other) < cooldown_seconds for other in taken_times):
            continue

        direction = "up" if ret >= 0 else "down"
        templates = UP_TEMPLATES if direction == "up" else DOWN_TEMPLATES
        template = templates[rng.integers(0, len(templates))]
        pct = f"{abs(ret) * 100:.1f}%"
        text = template.format(name=name, pct=pct)

        chosen.append(Headline(t=t, text=text, direction=direction, source=key))
        taken_times.append(t)

        if len(chosen) >= max_headlines:
            break

    chosen.sort(key=lambda h: h.t)
    return chosen
