/* Live candlestick chart, drawn on a <canvas>, synced to an <audio> element's
 * playback position. No video, no server-side rendering: candle data (from
 * /api/jobs/<id>) is drawn fresh every animation frame straight from
 * audio.currentTime, so scrubbing, pausing, and replaying all just work.
 */

class LiveCandleChart {
  constructor(canvas, { candles, candleDuration, startPrice, visibleCandles }) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.candles = candles; // [t_start, open, high, low, close, volume][]
    this.candleDuration = candleDuration;
    this.startPrice = startPrice;
    this.visible = visibleCandles || 45;

    this.colors = {
      bg: "#0a0507",
      grid: "#3a2128",
      bull: "#56a67e",
      bear: "#c1443c",
      ivory: "#efe6d8",
      ivoryDim: "#8a7a6d",
      brass: "#c8a24d",
    };

    // The price axis auto-scales to whatever's currently visible (see
    // draw()), not the whole track -- a quiet intro and a fortissimo
    // climax can differ hugely, and pinning the axis to the full range
    // squashes the quiet parts into a flat line. viewLo/viewHi hold the
    // current (EMA-smoothed) axis bounds between frames.
    this.viewLo = null;
    this.viewHi = null;

    this._resize();
    this._resizeHandler = () => this._resize();
    window.addEventListener("resize", this._resizeHandler);
  }

  destroy() {
    window.removeEventListener("resize", this._resizeHandler);
  }

  _resize() {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = Math.max(1, Math.round(rect.width * dpr));
    this.canvas.height = Math.max(1, Math.round(rect.height * dpr));
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.w = rect.width;
    this.h = rect.height;
  }

  _partial(c, frac) {
    frac = Math.max(0, Math.min(1, frac));
    const [t_start, open, high, low, close, volume] = c;
    const pClose = open + (close - open) * frac;
    let pHigh = high >= open ? open + (high - open) * frac : high;
    let pLow = low <= open ? open - (open - low) * frac : low;
    pHigh = Math.max(pHigh, open, pClose);
    pLow = Math.min(pLow, open, pClose);
    return [t_start, open, pHigh, pLow, pClose, volume * frac];
  }

  draw(currentTime) {
    const { ctx, w, h, colors } = this;
    const candles = this.candles;
    const n = candles.length;
    if (n === 0) return;

    let idxEnd = Math.min(Math.floor(currentTime / this.candleDuration), n - 1);
    idxEnd = Math.max(0, idxEnd);
    const idxStart = Math.max(0, idxEnd - this.visible + 1);
    const completed = candles.slice(idxStart, idxEnd);
    const cur = candles[idxEnd];
    const frac = (currentTime - cur[0]) / this.candleDuration;
    const live = this._partial(cur, frac);
    const window_ = completed.concat([live]);

    const t0 = window_[0][0];
    const t1 = cur[0] + this.candleDuration * 2;

    // Auto-scale the price axis to this visible window (including the
    // candle that's still forming), smoothed so it doesn't jump every
    // frame -- the same auto-zoom a real trading screen does as it scrolls.
    let localLo = Infinity, localHi = -Infinity;
    for (const c of window_) {
      if (c[3] < localLo) localLo = c[3];
      if (c[2] > localHi) localHi = c[2];
    }
    const localPad = (localHi - localLo) * 0.18 || localHi * 0.01 || 1;
    const targetLo = localLo - localPad, targetHi = localHi + localPad;
    if (this.viewLo === null) {
      this.viewLo = targetLo;
      this.viewHi = targetHi;
    } else {
      const ema = 0.12;
      this.viewLo += (targetLo - this.viewLo) * ema;
      this.viewHi += (targetHi - this.viewHi) * ema;
    }
    const chartTop = 14, chartBottom = h * 0.72;
    const volTop = h * 0.78, volBottom = h - 10;
    const padLeft = 8, padRight = 8;

    const xScale = (t) => padLeft + ((t - t0) / (t1 - t0)) * (w - padLeft - padRight);
    const yScale = (p) => chartTop + (1 - (p - this.viewLo) / (this.viewHi - this.viewLo)) * (chartBottom - chartTop);
    const volH = (v) => Math.max(v, 0.01) / 1.05 * (volBottom - volTop);

    ctx.fillStyle = colors.bg;
    ctx.fillRect(0, 0, w, h);

    // price gridlines
    ctx.strokeStyle = colors.grid;
    ctx.lineWidth = 1;
    ctx.font = "10px 'IBM Plex Mono', monospace";
    ctx.fillStyle = colors.ivoryDim;
    ctx.textBaseline = "middle";
    const gridLines = 4;
    for (let i = 0; i <= gridLines; i++) {
      const price = this.viewLo + (this.viewHi - this.viewLo) * (i / gridLines);
      const y = yScale(price);
      ctx.beginPath();
      ctx.moveTo(padLeft, y);
      ctx.lineTo(w - padRight, y);
      ctx.globalAlpha = 0.5;
      ctx.stroke();
      ctx.globalAlpha = 1;
      ctx.fillText(`$${price.toFixed(0)}`, padLeft + 4, y - 6);
    }

    const bodyWidth = Math.max(1.5, xScale(t0 + this.candleDuration * 0.7) - xScale(t0));

    const drawCandle = (c, isLive) => {
      const [t_start, open, high, low, close, volume] = c;
      const color = close >= open ? colors.bull : colors.bear;
      const x = xScale(t_start);

      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x + bodyWidth / 2, yScale(low));
      ctx.lineTo(x + bodyWidth / 2, yScale(high));
      ctx.stroke();

      const yOpenClose = [yScale(open), yScale(close)];
      const yTop = Math.min(...yOpenClose);
      let bodyH = Math.abs(yOpenClose[0] - yOpenClose[1]);
      bodyH = Math.max(bodyH, 1.2);
      ctx.fillStyle = color;
      ctx.fillRect(x, yTop, bodyWidth, bodyH);

      ctx.globalAlpha = 0.65;
      const vh = volH(volume);
      ctx.fillRect(x, volBottom - vh, bodyWidth, vh);
      ctx.globalAlpha = 1;

      if (isLive) {
        ctx.save();
        ctx.shadowColor = color;
        ctx.shadowBlur = 8;
        ctx.fillRect(x, yTop, bodyWidth, bodyH);
        ctx.restore();
      }
    };

    completed.forEach((c) => drawCandle(c, false));
    drawCandle(live, true);

    // running price label
    const priceColor = live[4] >= this.startPrice ? colors.bull : colors.bear;
    ctx.fillStyle = priceColor;
    ctx.font = "600 15px 'IBM Plex Mono', monospace";
    ctx.textAlign = "right";
    ctx.textBaseline = "alphabetic";
    ctx.fillText(`$${live[4].toFixed(2)}`, w - padRight, 26);
    ctx.textAlign = "left";
  }
}

window.LiveCandleChart = LiveCandleChart;
