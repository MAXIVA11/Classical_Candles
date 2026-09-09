# 🕯️ CLASSICAL CANDLES *(NYSE: MOZRT)*

> **PROSPECTUS** — This offering has not been approved or disapproved by the Securities and Exchange Commission, the New York Philharmonic, or anyone's mother. Past performance of the *Moonlight Sonata* is no guarantee of future adagios.

Somewhere, a Wall Street trader and a 19th-century violinist are furious this exists.

Paste a YouTube link to a piece of classical music. That's the entire prospectus. Classical Candles downloads the recording, listens closely, and takes it public: mints a ticker from the title, sets an opening price, and trades a live candlestick chart in perfect sync with the music. A fast, sharp violin run and the stock rips into a rally. A melody sliding downhill, and it's a sell-off. A long, held, sustained note, and the whole market just... yawns.

No render. No spinner. No "please wait." The chart is drawn live in your browser as the audio plays, the way a real trading floor reacts, except the trading floor is Vivaldi. Runs 100% on your machine. Your gains were never real.

![Made with Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Offline](https://img.shields.io/badge/runs-100%25%20offline-purple)
![Status](https://img.shields.io/badge/NOT-financial%20advice-critical)

`classical-music` `stock-market` `candlestick-chart` `audio-analysis` `music-visualization` `librosa` `data-sonification` `yt-dlp` `flask` `python`

---

## 📊 Today's closing bell

A sample of names already trading on the exchange, purely for flavor (your piece gets minted fresh, every time):

```
BTHVN5    Beethoven — Symphony No. 5          ▲ +14.2%
VVLDSUM   Vivaldi — Summer, Presto            ▲ +19.9%  🔥 most active
DEBUCLDL  Debussy — Clair de Lune             ▼  -4.3%
TCHYK1812 Tchaikovsky — 1812 Overture         ▲ +27.5%  halted, volatility
SATIEGY1  Satie — Gymnopédie No. 1            ▼  -0.6%  flat, thin volume
```

## 🔔 Go public in three commands

```bash
git clone https://github.com/MAXIVA11/Classical_Candles.git
cd Classical_Candles
pip install -r requirements.txt
python webapp/server.py
```

Open **http://127.0.0.1:5000**, paste a link, ring the opening bell. You'll also need [FFmpeg](https://ffmpeg.org/download.html) on your `PATH`, the one dependency older than the music itself.

No settings. No sliders. No flags to memorize. Candle speed, ticker symbol, and IPO price are all read straight off the recording. Want a file for your investors? Hit **Save as Video** once the chart's listed.

## 📜 Rules of the exchange

Every squeak, swell, and sixteenth note has consequences:

| Musical event | Market reaction |
|---|---|
| Melody climbs | 🟢 Green candle |
| Melody falls | 🔴 Red candle |
| Fast, sharp notes — trills, runs, aggressive bowing | Big candle, big volatility |
| Slow, sustained notes | Tiny candle, market's asleep |
| Bright, percussive hits | Long wick, like a spike someone panic-sold into |
| Loud passage | Tall volume bar |
| Tempo (BPM) | How fast the candles print |
| Piece title | Your ticker, your exchange, your IPO price |

A sleepy adagio opens flat as a Tuesday. The moment the strings hit an allegro, the whole thing breaks out like it just got acquired.

![demo chart](assets/demo_frame.png)

## 🏛️ Business overview (how it actually works)

1. **Acquisition** — `yt-dlp` fetches the recording.
2. **Due diligence** — `librosa` listens for loudness, attack sharpness, tempo, and melody direction.
3. **Underwriting** — the title gets hashed into a ticker symbol, an exchange, and an opening price.
4. **Trading** — those musical features get chopped into candles: open, high, low, close, volume, the whole ticket.
5. **The floor** — your browser paints the chart live on a `<canvas>`, locked to the `<audio>` element's own clock. No video file required, no waiting.
6. **Print a certificate** — want the file anyway? A `matplotlib` + `ffmpeg` pass bakes an MP4 on demand.

Prefer a terminal to a browser? `python main.py --url "..."` skips the trading floor entirely. `python main.py -h` for the full control panel.

## ⚠️ Risk factors

- **Market risk.** This is a sonification toy. It has never once predicted a real stock, and it never will.
- **Liquidity risk.** Your only exit strategy is closing the tab.
- **Concentration risk.** Do not put your rent money in the *Moonlight Sonata*, however tempting the chart looks at minute four.
- **Regulatory risk.** Only feed the exchange audio you actually have the right to use.
- **Key-person risk.** The "key person" is a dead composer. They cannot be reached for comment.

## 📄 Filed under

MIT licensed, see [LICENSE](LICENSE), for the three people who read licenses.
