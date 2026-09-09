"""Turn a piece of music into a stock ticker: symbol, exchange, and starting price.

Everything here is deterministic (seeded from the track title) so the same
piece always lists under the same symbol.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

_STOPWORDS = {
    "the", "a", "an", "in", "on", "of", "for", "and", "no", "op", "major",
    "minor", "movement", "mov", "official", "full", "hd", "audio", "video",
    "remastered", "version", "part", "live",
}

_EXCHANGES = [
    "Philharmonic Exchange (PHIL)",
    "Carnegie Index",
    "La Scala Bourse",
    "Vienna Musical Exchange (VME)",
    "Concert Hall Composite",
    "Conservatory Stock Exchange",
    "Symphony Over-the-Counter",
    "Maestro Global Markets",
]


@dataclass
class Ticker:
    symbol: str
    exchange: str
    issuer: str
    start_price: float


def _clean_words(title: str) -> list:
    words = re.findall(r"[A-Za-z]+", title)
    significant = [w for w in words if w.lower() not in _STOPWORDS]
    return significant or words or ["OPUS"]


def _make_symbol(title: str) -> str:
    words = _clean_words(title)

    if len(words) == 1:
        symbol = words[0][:4].upper()
    else:
        symbol = "".join(w[0] for w in words).upper()
        if len(symbol) < 3:
            symbol += words[0][1:4].upper()
        symbol = symbol[:5]

    symbol = re.sub(r"[^A-Z]", "", symbol)
    return symbol[:5] if len(symbol) >= 3 else (symbol + "OPUS")[:4]


def generate_ticker(title: str) -> Ticker:
    digest = hashlib.sha256(title.encode("utf-8")).hexdigest()
    seed = int(digest[:8], 16)

    symbol = _make_symbol(title)
    exchange = _EXCHANGES[seed % len(_EXCHANGES)]
    start_price = round(35.0 + (seed % 26500) / 100.0, 2)  # $35 - $300 IPO price

    return Ticker(symbol=symbol, exchange=exchange, issuer=title, start_price=start_price)
