# Classical Candles

**What if Beethoven had a Bloomberg terminal?**

Paste a YouTube link to a piece of classical music. That's the entire interface. Classical Candles downloads the recording, listens to it, and lists it on the exchange: a ticker symbol is minted from the piece's title, a starting price is set, and a candlestick chart trades live in your browser, in perfect sync with the actual audio playback. When the violins turn sharp and fast, the market rallies hard. When the melody falls or the passage goes quiet, it slides.

This isn't a pre-rendered video you wait for. The chart is drawn frame by frame straight from the `<audio>` element's own playback position, so you can pause, scrub, and replay, and the candles follow along exactly. An MP4 export is available on demand for anyone who wants a file to share.

Runs entirely on your own machine. No exchange, orchestra, or savings account was harmed in the making of this chart.

![Made with Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Offline](https://img.shields.io/badge/runs-100%25%20offline-purple)
![Status](https://img.shields.io/badge/status-for%20fun-orange)

`classical-music` `stock-market` `candlestick-chart` `audio-analysis` `music-visualization` `librosa` `data-sonification` `generative-art` `yt-dlp` `flask` `python`

---

## The website

Run one command, open your browser, paste a link. That's it, there are no settings to tune, no flags to remember. Candle length, chart zoom, and starting price are all worked out automatically from the recording itself.

```bash
python webapp/server.py
```

Then open **http://127.0.0.1:5000** and drop in a YouTube URL.

The page opens like a trading desk built for a concert hall: a ticker tape of fictional composer stocks scrolls overhead, you feed the exchange a link, and press **Ring the Opening Bell**. A paper tape prints the pipeline's progress in real time ("Tracking melody pitch...", "Translating the score into ticks..."). When the listing is ready, you get a stock certificate for the piece: its minted ticker symbol, exchange, open, high, low, close, tempo, and volume, sitting above a live candlestick chart and the audio player itself. Press play, and the market opens with the music.

Want a file instead of a browser tab? Press **Save as Video** on the certificate and an MP4 renders in the background, ready to download when it's done.

## The market rules

This is the actual mapping from sound to price, no black box:

| Musical event | Market reaction |
|---|---|
| Melody pitch rises | Candle turns **green** (bullish) |
| Melody pitch falls | Candle turns **red** (bearish) |
| Sharp *and* fast notes (rapid bowing, trills, runs) | Bigger candle body, higher volatility, the price moves hard |
| Slow, sustained, calm notes | Small candle body, the market goes quiet |
| Bright, percussive transients | Longer wicks, like a sudden spike or rejection |
| Loud passages | Taller volume bars |
| Quiet passages | Thin volume bars |
| Overall tempo (BPM) | Sets how long each candle lasts, so a presto and an adagio don't trade at the same speed |
| Piece title | Minted into a ticker symbol, an exchange listing, and a starting price |

A slow adagio opening looks like a flat, sleepy market. The moment the strings launch into a fast, sharp allegro run, the chart breaks out into a rally, or a crash, depending on where the melody is headed.

## How it works under the hood

1. **Download** — `yt-dlp` grabs the audio from the link.
2. **Listen** — [`librosa`](https://librosa.org/) analyzes the waveform frame by frame: loudness, onset strength (attack sharpness), onset density (how many sharp attacks per second), spectral brightness, tempo, and melody pitch (via `pyin` tracking).
3. **List it** — the piece's title is hashed into a deterministic ticker symbol, exchange name, and starting price, so the same recording always lists the same way.
4. **Trade** — those musical features are chopped into time windows (their length set automatically from the detected tempo) and mapped into OHLCV candle data. This step is the only one the server does; there is no per-frame video work.
5. **Chart it, live** — the candle data and the audio file are handed to the browser. A `<canvas>` element redraws the chart on every `timeupdate` from the `<audio>` element, so the visual is always exactly wherever the music actually is, no separate render pass required.
6. **Export it, optionally** — pressing "Save as Video" runs the same candle data through a `matplotlib` + `ffmpeg` pipeline on the server to produce a shareable MP4.

### Why the video export is fast

Early versions of this pipeline rebuilt the entire chart from scratch on every single video frame, which meant redrawing every visible candle thousands of times over a multi-minute track. The renderer now treats completed candles as a static background image, recaptured only when a new candle finishes, and blits just the one currently-forming candle on top of it every frame. That cut full-track render time by roughly 8x.

## Demo

A calm sustained passage followed by a fast rising violin run: the chart stays flat, then rallies hard exactly when the run kicks in.

![demo chart](assets/demo_frame.png)

## Requirements

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) installed and on your `PATH` (used for audio extraction and, only if you export a video, encoding and muxing)

## Install

```bash
git clone https://github.com/MAXIVA11/Classical_Candles.git
cd Classical_Candles
pip install -r requirements.txt
```

## Run it

```bash
python webapp/server.py
```

Open **http://127.0.0.1:5000**, paste a YouTube link, ring the bell, press play.

### Command line, for scripting

The website is the main way to use this, but the pipeline is also available without a browser, for anyone who wants to script it, batch a playlist, or go straight to an MP4 file:

```bash
python main.py --url "https://www.youtube.com/watch?v=XXXXXXXXXXX"
python main.py --input-audio "my_song.mp3"
```

Run `python main.py -h` for the full list of tunable options (candle length, starting price, visible window, and so on). The website skips all of that and chooses sensible values from the recording automatically.

## Project layout

```
classical_candles/
  downloader.py    yt-dlp wrapper: URL to WAV
  analysis.py      librosa feature extraction: WAV to per-frame features
  ticker.py        mints a ticker symbol, exchange, and starting price from the title
  auto_params.py   picks candle length and chart parameters from the detected tempo
  candles.py       the music-to-market mapping: features to OHLCV candles
  render.py        matplotlib + ffmpeg pipeline for the optional MP4 export
  cli.py           command-line entry point
webapp/
  server.py        Flask app: downloads, analyzes, serves candle data + audio, renders video on demand
  static/
    index.html     the trading-desk page
    style.css      the concert-hall-meets-terminal look
    chart.js       the live candlestick renderer, driven by the <audio> element
    app.js         wires the form, progress tape, and certificate together
main.py            command-line entry point
```

## Notes & disclaimers

- This is a sonification and visualization toy, not a real trading signal, financial product, or investment advice. Please do not put your savings into the "Moonlight Sonata."
- Only download audio you have the right to use. Respect YouTube's Terms of Service and copyright law in your jurisdiction.
- Melody pitch tracking (`pyin`) is the slowest step in the analysis, expect it to take a noticeable chunk of the track's own runtime, especially on long pieces.

## License

MIT, see [LICENSE](LICENSE).
