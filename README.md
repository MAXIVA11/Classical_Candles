# Classical Candles

**What if Beethoven had a Bloomberg terminal?**

Paste a YouTube link to a piece of classical music. That's it, that's the whole interface. Classical Candles downloads it, listens to it, and lists it on the exchange: it mints a ticker symbol from the title, sets a starting price, and trades a live candlestick chart in sync with the music. Sharp, fast violin runs send the price rocketing. A falling melody dumps it. A calm sustained note just... consolidates.

No pre-rendered video, no waiting around: the chart is drawn live in your browser as the audio plays. Runs 100% on your machine.

![Made with Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Offline](https://img.shields.io/badge/runs-100%25%20offline-purple)
![Status](https://img.shields.io/badge/status-for%20fun-orange)

`classical-music` `stock-market` `candlestick-chart` `audio-analysis` `music-visualization` `librosa` `data-sonification` `yt-dlp` `flask` `python`

---

## Try it

```bash
git clone https://github.com/MAXIVA11/Classical_Candles.git
cd Classical_Candles
pip install -r requirements.txt
python webapp/server.py
```

Open **http://127.0.0.1:5000**, paste a link, ring the bell. Needs [FFmpeg](https://ffmpeg.org/download.html) on your `PATH`.

That's the whole setup. No config, no flags, the site figures out candle speed and starting price from the recording itself. Want an MP4 to keep? Hit **Save as Video** once your chart is listed.

## The market rules

| Musical event | Market reaction |
|---|---|
| Melody rises | Green candle |
| Melody falls | Red candle |
| Sharp, fast notes (trills, runs, rapid bowing) | Big candle, high volatility |
| Slow, sustained notes | Small candle, quiet market |
| Bright, percussive hits | Long wicks, like a spike |
| Loud passage | Tall volume bar |
| Tempo (BPM) | Sets how fast candles print |
| Piece title | Becomes the ticker, exchange, and IPO price |

A sleepy adagio opening trades flat. The second the strings launch into a fast allegro run, watch it break out.

![demo chart](assets/demo_frame.png)

## How it actually works

1. `yt-dlp` grabs the audio.
2. `librosa` listens for loudness, attack sharpness, tempo, and melody pitch.
3. The title gets hashed into a ticker, exchange, and starting price.
4. Those musical features get sliced into candles (OHLCV).
5. Your browser draws the chart live on a `<canvas>`, synced to the `<audio>` element, no video required.
6. Want a file? A `matplotlib` + `ffmpeg` pass renders an MP4 on demand.

Prefer the terminal? `python main.py --url "..."` works too, run `python main.py -h` for options.

## Fine print

Sonification toy, not financial advice, please don't invest your rent money in the *Moonlight Sonata*. Only download audio you have the right to use.

MIT licensed, see [LICENSE](LICENSE).
