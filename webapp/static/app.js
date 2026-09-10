(() => {
  const TAPE_QUOTES = [
    ["BTHVN5", "+14.2%", "up"], ["MOZK550", "-2.1%", "down"],
    ["BACHGDB", "+31.7%", "up"], ["CHPNNOC", "+8.4%", "up"],
    ["VVLDSUM", "+19.9%", "up"], ["DEBUCLDL", "-4.3%", "down"],
    ["BRAHMS4", "+6.6%", "up"], ["SCHBRTU", "-1.8%", "down"],
    ["HNDLMSC", "+11.0%", "up"], ["TCHYK1812", "+27.5%", "up"],
    ["RVLBOLR", "+9.3%", "up"], ["SATIEGY1", "-0.6%", "down"],
  ];

  function buildTape() {
    const track = document.getElementById("tapeTrack");
    const line = TAPE_QUOTES.map(
      ([sym, pct, dir]) => `<span>${sym} <span class="${dir}">${pct}</span></span>`
    ).join("");
    track.innerHTML = line + line; // duplicated for seamless scroll loop
  }

  function formatTime(seconds) {
    if (!isFinite(seconds) || seconds < 0) seconds = 0;
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${String(s).padStart(2, "0")}`;
  }

  const form = document.getElementById("tickerForm");
  const urlInput = document.getElementById("urlInput");
  const bellButton = document.getElementById("bellButton");
  const formHint = document.getElementById("formHint");
  const tapeRoll = document.getElementById("tapeRoll");
  const tapeStrip = document.getElementById("tapeStrip");
  const certificate = document.getElementById("certificate");
  const errorBanner = document.getElementById("errorBanner");
  const againButton = document.getElementById("againButton");
  const videoButton = document.getElementById("videoButton");
  const videoStatus = document.getElementById("videoStatus");
  const audioEl = document.getElementById("certAudio");
  const canvas = document.getElementById("liveCanvas");
  const liveDot = document.querySelector(".live-dot");
  const liveElapsed = document.getElementById("liveElapsed");
  const liveTotal = document.getElementById("liveTotal");

  let pollTimer = null;
  let videoPollTimer = null;
  let seenLogLines = 0;
  let chart = null;
  let rafId = null;
  let currentJobId = null;

  function showError(msg) {
    errorBanner.textContent = msg;
    errorBanner.hidden = false;
  }

  function clearError() {
    errorBanner.hidden = true;
    errorBanner.textContent = "";
  }

  function resetForm() {
    bellButton.disabled = false;
    bellButton.querySelector(".bell-glyph").textContent = "♫";
    formHint.textContent = "One link. We handle the tempo, the ticker, and the tape.";
  }

  function appendTapeLines(lines) {
    lines.forEach((text) => {
      const el = document.createElement("div");
      el.className = "tape-line";
      el.textContent = text;
      tapeStrip.appendChild(el);
    });
    tapeStrip.querySelectorAll(".tape-line.current").forEach((el) => el.classList.remove("current"));
    if (tapeStrip.lastElementChild) tapeStrip.lastElementChild.classList.add("current");
    tapeRoll.scrollTop = tapeRoll.scrollHeight;
  }

  function stopLoop() {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
    liveDot.classList.remove("playing");
  }

  function loop() {
    if (!chart) return;
    chart.draw(audioEl.currentTime);
    liveElapsed.textContent = formatTime(audioEl.currentTime);
    if (!audioEl.paused && !audioEl.ended) {
      rafId = requestAnimationFrame(loop);
    } else {
      stopLoop();
    }
  }

  function setupChart(result) {
    if (chart) chart.destroy();
    chart = new window.LiveCandleChart(canvas, {
      candles: result.candles,
      candleDuration: result.candle_duration,
      startPrice: result.open,
      visibleCandles: 45,
    });
    chart.draw(0);
    liveTotal.textContent = formatTime(result.duration);
    liveElapsed.textContent = "0:00";

    audioEl.src = result.audio_url;
    audioEl.onplay = () => {
      liveDot.classList.add("playing");
      if (!rafId) rafId = requestAnimationFrame(loop);
    };
    audioEl.onpause = () => {
      stopLoop();
      chart.draw(audioEl.currentTime);
    };
    audioEl.onended = () => {
      stopLoop();
      chart.draw(audioEl.duration || result.duration);
    };
    audioEl.onseeking = () => chart.draw(audioEl.currentTime);
    audioEl.onseeked = () => chart.draw(audioEl.currentTime);
    // Fallback tick independent of requestAnimationFrame: fires on its own
    // clock during playback (roughly 4x/sec per spec) so the chart still
    // advances even in contexts where rAF gets throttled (backgrounded or
    // minimized windows), not just when the tab has an active paint loop.
    audioEl.ontimeupdate = () => {
      chart.draw(audioEl.currentTime);
      liveElapsed.textContent = formatTime(audioEl.currentTime);
    };

    // Open the market the moment it's listed -- try to start playback
    // automatically rather than making the user hunt for a play button.
    // Browsers can still block unmuted autoplay outside a fresh user
    // gesture; if that happens we just fall back to "press play" instead
    // of erroring.
    audioEl.play().then(
      () => { formHint.textContent = "Market open."; },
      () => { formHint.textContent = "Listed. Press play below."; }
    );
  }

  function renderResult(result) {
    document.getElementById("certExchange").textContent = result.exchange;
    document.getElementById("certSymbol").textContent = result.symbol;
    document.getElementById("certIssuer").textContent = result.issuer;

    const changeEl = document.getElementById("certChange");
    const arrowEl = document.getElementById("certArrow");
    const pctEl = document.getElementById("certChangePct");
    const bullish = result.change_pct >= 0;
    changeEl.classList.remove("bull", "bear");
    changeEl.classList.add(bullish ? "bull" : "bear");
    arrowEl.classList.toggle("down", !bullish);
    pctEl.textContent = `${bullish ? "+" : ""}${result.change_pct.toFixed(1)}%`;

    document.getElementById("statOpen").textContent = `$${result.open.toFixed(2)}`;
    document.getElementById("statClose").textContent = `$${result.close.toFixed(2)}`;
    document.getElementById("statHigh").textContent = `$${result.high.toFixed(2)}`;
    document.getElementById("statLow").textContent = `$${result.low.toFixed(2)}`;
    document.getElementById("statTempo").textContent = `${result.tempo} BPM`;
    document.getElementById("statDuration").textContent = formatTime(result.duration);
    document.getElementById("statVolume").textContent = result.volume.toLocaleString("en-US");
    document.getElementById("statCandles").textContent = result.candles.length;

    videoButton.textContent = "Save as Video";
    videoButton.disabled = false;
    videoStatus.hidden = true;

    certificate.hidden = false;
    setupChart(result);
    certificate.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function poll(jobId) {
    try {
      const res = await fetch(`/api/jobs/${jobId}`);
      const job = await res.json();

      if (job.log && job.log.length > seenLogLines) {
        appendTapeLines(job.log.slice(seenLogLines));
        seenLogLines = job.log.length;
      }

      if (job.status === "done") {
        clearInterval(pollTimer);
        formHint.textContent = "Listed. Press play below.";
        renderResult(job.result);
        resetForm();
      } else if (job.status === "error") {
        clearInterval(pollTimer);
        showError(job.error || "The exchange halted trading unexpectedly.");
        resetForm();
      }
    } catch (err) {
      clearInterval(pollTimer);
      showError("Lost the line to the exchange floor. Try again.");
      resetForm();
    }
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearError();
    certificate.hidden = true;
    stopLoop();
    if (chart) { chart.destroy(); chart = null; }

    const url = urlInput.value.trim();
    if (!url) return;

    bellButton.disabled = true;
    bellButton.querySelector(".bell-glyph").textContent = "⏳";
    formHint.textContent = "Opening the market...";
    tapeRoll.hidden = false;
    tapeStrip.innerHTML = "";
    seenLogLines = 0;

    try {
      const res = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();

      if (!res.ok) {
        showError(data.error || "Couldn't open the market for that link.");
        resetForm();
        return;
      }

      currentJobId = data.job_id;
      pollTimer = setInterval(() => poll(data.job_id), 1000);
      poll(data.job_id);
    } catch (err) {
      showError("Couldn't reach the exchange. Is the server running?");
      resetForm();
    }
  });

  videoButton.addEventListener("click", async () => {
    if (!currentJobId) return;
    videoButton.disabled = true;
    videoStatus.hidden = false;
    videoStatus.textContent = "Rendering the video...";

    try {
      await fetch(`/api/jobs/${currentJobId}/video`, { method: "POST" });
    } catch (err) {
      videoStatus.textContent = "Couldn't start the render.";
      videoButton.disabled = false;
      return;
    }

    videoPollTimer = setInterval(async () => {
      try {
        const res = await fetch(`/api/jobs/${currentJobId}/video`);
        const v = await res.json();
        if (v.status === "rendering") {
          videoStatus.textContent = `Rendering the video... ${v.percent || 0}%`;
        } else if (v.status === "done") {
          clearInterval(videoPollTimer);
          videoStatus.innerHTML = `Ready. <a href="${v.video_url}" download>Download the MP4</a>`;
          videoButton.hidden = true;
        } else if (v.status === "error") {
          clearInterval(videoPollTimer);
          videoStatus.textContent = v.error || "The render failed.";
          videoButton.disabled = false;
        }
      } catch (err) {
        clearInterval(videoPollTimer);
        videoStatus.textContent = "Lost contact with the render job.";
        videoButton.disabled = false;
      }
    }, 1500);
  });

  againButton.addEventListener("click", () => {
    stopLoop();
    if (chart) { chart.destroy(); chart = null; }
    audioEl.pause();
    audioEl.src = "";
    certificate.hidden = true;
    tapeRoll.hidden = true;
    videoButton.hidden = false;
    urlInput.value = "";
    urlInput.focus();
    clearError();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  buildTape();
})();
