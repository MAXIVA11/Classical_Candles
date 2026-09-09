# Classical Candles 🕯️📈

**Somewhere, a Wall Street trader and a 19th-century violinist are furious this exists.**

Paste a YouTube link to a piece of classical music. That's it. That's the whole app. Classical Candles downloads it, listens closely, and takes it public: mints a ticker symbol from the title, sets an opening price, and trades a live candlestick chart in perfect sync with the music. A fast, sharp violin run sends the stock into a full-blown rally. A melody sliding downhill? Sell-off. A long, calm, sustained note? The market yawns and consolidates.

No render, no spinner, no "please wait." The chart is drawn live in your browser as the audio plays, like ringing the opening bell for an orchestra. 100% offline. Your portfolio was never real to begin with.

![Made with Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Offline](https://img.shields.io/badge/runs-100%25%20offline-purple)
![Status](https://img.shields.io/badge/status-not%20financial%20advice-orange)

`classical-music` `stock-market` `candlestick-chart` `audio-analysis` `music-visualization` `librosa` `data-sonification` `yt-dlp` `flask` `python`

---

## Go public in three commands

```bash
git clone https://github.com/MAXIVA11/Classical_Candles.git
cd Classical_Candles
pip install -r requirements.txt
python webapp/server.py
```

Open **http://127.0.0.1:5000**, paste a link, ring the bell, watch the strings move markets. You'll also need [FFmpeg](https://ffmpeg.org/download.html) on your `PATH`, the one dependency older than the music itself.

No settings, no sliders, no flags to memorize. Candle speed and IPO price are read straight from the recording. Want proof for your investors? Hit **Save as Video** once the chart's listed.

## The rules of the market

Every squeak, swell, and sixteenth note has consequences:

| Musical event | Market reaction |
|---|---|
| Melody climbs | Green candle |
| Melody falls | Red candle |
| Fast, sharp notes (trills, runs, aggressive bowing) | Big candle, big volatility |
| Slow, sustained notes | Tiny candle, market's asleep |
| Bright, percussive hits | Long wicks, like a spike someone panic-sold into |
| Loud passage | Tall volume bar |
| Tempo (BPM) | How fast the candles print |
| Piece title | Your ticker, your exchange, your IPO price |

A sleepy adagio opens flat as a Tuesday. Then the strings hit an allegro and the whole thing breaks out like it just got acquired.

![demo chart](assets/demo_frame.png)

## What's actually happening under the hood

1. `yt-dlp` fetches the recording.
2. `librosa` listens for loudness, attack sharpness, tempo, and melody direction.
3. The title gets hashed into a ticker symbol, an exchange, and a starting price.
4. Those musical features get chopped into candles (open, high, low, close, volume, the whole ticket).
5. Your browser paints the chart live on a `<canvas>`, locked to the `<audio>` element's clock. No video file required.
6. Want the file anyway? A `matplotlib` + `ffmpeg` pass bakes an MP4 on demand.

Terminal person? `python main.py --url "..."` skips the browser entirely. `python main.py -h` for the full control panel.

## Fine print, read by absolutely no one

This is a sonification toy, not a trading signal, not investment advice, and definitely not a reason to mortgage anything for the *Moonlight Sonata*. Only feed it audio you have the right to use. Past performance of Vivaldi's *Summer* does not guarantee future adagios.

MIT licensed. See [LICENSE](LICENSE) if you're the type who reads licenses.
