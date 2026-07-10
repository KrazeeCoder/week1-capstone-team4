// ============================================================
//  404 FILE FOUND — "Uncharted"
//  Starfield + real-peak constellation, wired to the Flask
//  pipeline (/api/match, /api/songs).
// ============================================================

const RM = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const CYAN = css("--cyan") || "#38bdf8";
const VIOLET = css("--violet") || "#c084fc";

// ---------- shared helpers ----------

function encodeWav(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const s8 = (o, str) => { for (let i = 0; i < str.length; i++) view.setUint8(o + i, str.charCodeAt(i)); };
  s8(0, "RIFF"); view.setUint32(4, 36 + samples.length * 2, true);
  s8(8, "WAVE"); s8(12, "fmt ");
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  s8(36, "data"); view.setUint32(40, samples.length * 2, true);
  let o = 44;
  for (let i = 0; i < samples.length; i++, o += 2) {
    const v = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(o, v < 0 ? v * 0x8000 : v * 0x7fff, true);
  }
  return new Blob([buffer], { type: "audio/wav" });
}

async function postAudio(url, blob, fields) {
  const form = new FormData();
  form.append("audio", blob, blob.name || "clip.wav");
  for (const [k, v] of Object.entries(fields || {})) form.append(k, v);
  const resp = await fetch(url, { method: "POST", body: form });
  const data = await resp.json().catch(() => ({}));
  return { ok: resp.ok, status: resp.status, data };
}

function statsText(stats) {
  if (!stats) return "";
  return `${stats.num_peaks} stars · ${stats.duration_seconds}s · ${stats.sample_rate} Hz`;
}

// ---------- starfield ----------

const sky = document.getElementById("starfield");
const skyCtx = sky.getContext("2d");
let stars = [];

function seedStars() {
  const r = sky.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  sky.width = r.width * dpr; sky.height = r.height * dpr;
  skyCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const count = Math.min(140, Math.floor((r.width * r.height) / 14000));
  stars = Array.from({ length: count }, (_, i) => ({
    x: (Math.sin(i * 12.9898) * 43758.5453 % 1 + 1) % 1 * r.width,
    y: (Math.sin(i * 78.233) * 12543.123 % 1 + 1) % 1 * r.height,
    r: 0.4 + ((i * 7) % 10) / 8,
    a: 0.2 + ((i * 13) % 10) / 14,
    tw: (i % 10) / 10 * Math.PI * 2,
    vy: 0.02 + ((i * 3) % 5) / 260,
  }));
}

function drawStars(t) {
  const r = sky.getBoundingClientRect();
  skyCtx.clearRect(0, 0, r.width, r.height);
  for (const s of stars) {
    if (!RM) {
      s.y += s.vy;
      if (s.y > r.height + 2) s.y = -2;
    }
    const twinkle = RM ? 1 : 0.6 + 0.4 * Math.sin(t * 0.001 + s.tw);
    skyCtx.beginPath();
    skyCtx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
    skyCtx.fillStyle = `rgba(226,232,255,${(s.a * twinkle).toFixed(3)})`;
    skyCtx.fill();
  }
}
window.addEventListener("resize", seedStars);

// ---------- constellation (real peaks) ----------

const scope = document.getElementById("constellation");
const scopeCtx = scope.getContext("2d");
const scopeEmpty = document.getElementById("scope-empty");
let points = [];       // {x, y, delay}
let lines = [];        // [i, j]
let plotStart = null;
let plotHue = CYAN;
let recording = null;  // active capture session while the mic is open

function sizeScope() {
  const r = scope.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  scope.width = Math.max(1, r.width * dpr);
  scope.height = Math.max(1, r.height * dpr);
  scopeCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
window.addEventListener("resize", sizeScope);

function plotConstellation(peaksXY, hue) {
  plotHue = hue || CYAN;
  points = (peaksXY || []).map((p, i) => ({ x: p[0], y: 1 - p[1], delay: i / Math.max(1, peaksXY.length) }));
  // fanout: link each anchor to a few near-future points (the fingerprint pairing)
  lines = [];
  for (let i = 0; i < points.length; i++) {
    let made = 0;
    for (let j = i + 1; j < points.length && made < 3; j++) {
      const dx = points[j].x - points[i].x, dy = points[j].y - points[i].y;
      if (dx > 0.008 && dx < 0.16 && Math.abs(dy) < 0.22) { lines.push([i, j]); made++; }
    }
  }
  plotStart = null;
  scopeEmpty.classList.add("gone");
}

function hexToRgb(h) {
  const n = parseInt(h.replace("#", ""), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function drawConstellation(t) {
  const r = scope.getBoundingClientRect();
  const w = r.width, h = r.height;
  const padX = 18, padY = 16;
  const px = (x) => padX + x * (w - padX * 2);
  const py = (y) => padY + y * (h - padY * 2);
  scopeCtx.clearRect(0, 0, w, h);
  if (!points.length) return;

  if (plotStart === null) plotStart = t;
  const DUR = RM ? 1 : 1100;
  const prog = RM ? 1 : Math.min(1, (t - plotStart) / DUR);
  const [cr, cg, cb] = hexToRgb(plotHue);
  const vis = (p) => Math.max(0, Math.min(1, (prog - p.delay * 0.55) / 0.45));

  // fanout lines
  scopeCtx.lineWidth = 1;
  for (const [i, j] of lines) {
    const a = Math.min(vis(points[i]), vis(points[j]));
    if (a <= 0.02) continue;
    scopeCtx.strokeStyle = `rgba(${cr},${cg},${cb},${(a * 0.22).toFixed(3)})`;
    scopeCtx.beginPath();
    scopeCtx.moveTo(px(points[i].x), py(points[i].y));
    scopeCtx.lineTo(px(points[j].x), py(points[j].y));
    scopeCtx.stroke();
  }
  // stars
  for (const p of points) {
    const a = vis(p);
    if (a <= 0.02) continue;
    const x = px(p.x), y = py(p.y), rad = 1.4 + a * 1.6;
    scopeCtx.beginPath();
    scopeCtx.arc(x, y, rad, 0, Math.PI * 2);
    scopeCtx.fillStyle = `rgba(${cr},${cg},${cb},${a.toFixed(3)})`;
    scopeCtx.shadowColor = plotHue;
    scopeCtx.shadowBlur = 8 * a;
    scopeCtx.fill();
  }
  scopeCtx.shadowBlur = 0;
}

// ---------- live mic waveform (while recording) ----------

function drawLive() {
  const r = scope.getBoundingClientRect();
  const w = r.width, h = r.height, mid = h / 2;
  scopeCtx.clearRect(0, 0, w, h);
  if (!recording) return;
  const data = recording.timeData;
  recording.analyser.getByteTimeDomainData(data);
  const step = 2;
  const slice = w / (data.length / step);
  scopeCtx.lineWidth = 2;
  scopeCtx.strokeStyle = CYAN;
  scopeCtx.shadowColor = CYAN;
  scopeCtx.shadowBlur = 12;
  scopeCtx.beginPath();
  let x = 0;
  for (let i = 0; i < data.length; i += step, x += slice) {
    const v = (data[i] - 128) / 128;
    const y = mid + v * mid * 0.92;
    i === 0 ? scopeCtx.moveTo(0, y) : scopeCtx.lineTo(x, y);
  }
  scopeCtx.stroke();
  scopeCtx.shadowBlur = 0;
}

// ---------- single animation loop ----------

function frame(t) {
  drawStars(t);
  if (recording) drawLive();
  else drawConstellation(t);
  requestAnimationFrame(frame);
}
seedStars(); sizeScope();
requestAnimationFrame(frame);

// ---------- result rendering ----------

const STATUS_LABEL = { 200: "file found", 202: "indexing", 403: "mic blocked", 404: "not found", 500: "scan failed" };

function showResult(el, kind, code, opts = {}) {
  el.className = "result " + kind;
  const label = opts.label || STATUS_LABEL[code] || "";
  const codeHtml = (code === null || code === undefined) ? "" : `<span class="code">${code}</span> `;
  let html = `<span class="status">${codeHtml}${escapeHtml(label)}</span>`;
  if (opts.title) html += `<div class="result-title">${escapeHtml(opts.title)}</div>`;
  if (opts.msg) html += `<div class="result-msg">${escapeHtml(opts.msg)}</div>`;
  if (opts.stats) html += `<div class="result-stats">${escapeHtml(statsText(opts.stats))}</div>`;
  (opts.notes || []).forEach((n) => { html += `<div class="result-note">note — ${escapeHtml(n)}</div>`; });
  el.innerHTML = html;
  el.classList.remove("enter"); void el.offsetWidth; el.classList.add("enter");
}

function escapeHtml(s) {
  const d = document.createElement("div"); d.textContent = s == null ? "" : String(s); return d.innerHTML;
}

// ---------- identify (mic + upload) ----------

const matchResult = document.getElementById("match-result");
const scanBtn = document.getElementById("scan-btn");
const scanText = document.getElementById("scan-text");

async function identify(blob) {
  showResult(matchResult, "scan", "···", { label: "charting", title: "Reading your signal…" });
  try {
    const { ok, status, data } = await postAudio("/api/match", blob);
    if (!ok) { showResult(matchResult, "err", status || 500, { msg: data.error || "Something went wrong on the server." }); return; }
    if (data.stats && data.stats.peaks_xy) plotConstellation(data.stats.peaks_xy, data.match ? VIOLET : CYAN);
    if (data.match) {
      showResult(matchResult, "ok", 200, { title: data.match, msg: "Matched against the library.", stats: data.stats });
    } else {
      showResult(matchResult, "charted", null, { label: "signal charted", stats: data.stats });
    }
  } catch (err) {
    showResult(matchResult, "err", 500, { msg: err.message });
  }
}

// ---------- microphone capture (tap to start, tap to stop) ----------

scanBtn.addEventListener("click", () => {
  if (recording) stopRecording();
  else startRecording();
});

async function startRecording() {
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    showResult(matchResult, "err", 403, {
      title: "Microphone blocked",
      msg: "Allow mic access in your browser, or use “Load a .wav clip” instead.",
    });
    return;
  }

  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const source = ctx.createMediaStreamSource(stream);
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 2048;
  const timeData = new Uint8Array(analyser.fftSize);
  source.connect(analyser);

  const processor = ctx.createScriptProcessor(4096, 1, 1);
  const chunks = [];
  processor.onaudioprocess = (e) => chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
  source.connect(processor);
  processor.connect(ctx.destination);

  recording = { ctx, stream, source, analyser, timeData, processor, chunks };

  points = [];                          // clear any previous constellation
  matchResult.classList.add("hidden");  // hide previous result
  scopeEmpty.classList.add("gone");
  scanBtn.classList.add("recording");
  scanText.textContent = "Stop listening";
}

async function stopRecording() {
  const r = recording;
  recording = null;
  scanBtn.classList.remove("recording");
  scanText.textContent = "Scan a song";

  r.processor.disconnect();
  r.source.disconnect();
  r.analyser.disconnect();
  r.stream.getTracks().forEach((t) => t.stop());

  const total = r.chunks.reduce((n, c) => n + c.length, 0);
  if (!total) { await r.ctx.close(); scopeEmpty.classList.remove("gone"); return; }
  const samples = new Float32Array(total);
  let pos = 0;
  for (const c of r.chunks) { samples.set(c, pos); pos += c.length; }
  const blob = encodeWav(samples, r.ctx.sampleRate);
  await r.ctx.close();

  identify(blob);
}

// ---------- file upload (identify) ----------

document.getElementById("clip-file").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file) identify(file);
  e.target.value = "";
});

// ---------- library ----------

const grid = document.getElementById("songs-grid");

async function refreshSongs() {
  try {
    const resp = await fetch("/api/songs");
    const data = await resp.json();
    if (!data.songs || !data.songs.length) {
      grid.innerHTML = `<div class="library-empty"><strong>No tracks charted yet</strong>Add the first one below, then scan a clip to find it.</div>`;
      return;
    }
    grid.innerHTML = data.songs.map((s, i) => `
      <article class="song-card" style="animation-delay:${i * 45}ms">
        <div class="song-id">ID ${escapeHtml(String(s.song_id).padStart(3, "0"))}</div>
        <div class="song-title">${escapeHtml(s.title)}</div>
        <div class="song-artist">${escapeHtml(s.artist)}</div>
        <div class="song-file">${escapeHtml(s.filename)}</div>
      </article>`).join("");
  } catch {
    grid.innerHTML = `<div class="library-empty"><strong>Can't reach the database</strong>Is the server still running?</div>`;
  }
}

// ---------- add form ----------

const addForm = document.getElementById("add-form");
const addButton = document.getElementById("add-button");
const addResult = document.getElementById("add-result");
const titleInput = document.getElementById("song-title");
const artistInput = document.getElementById("song-artist");
const songFile = document.getElementById("song-file");
const songFileName = document.getElementById("song-file-name");
const fileDrop = document.getElementById("file-drop");

songFile.addEventListener("change", () => {
  if (songFile.files[0]) {
    songFileName.textContent = songFile.files[0].name;
    fileDrop.classList.add("filled");
  } else {
    songFileName.textContent = "Choose a .wav file";
    fileDrop.classList.remove("filled");
  }
});

addForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  // inline validation — mark and focus the first empty required field
  const checks = [[titleInput, titleInput.value.trim()], [artistInput, artistInput.value.trim()]];
  let firstBad = null;
  for (const [el, val] of checks) {
    el.classList.toggle("invalid", !val);
    if (!val && !firstBad) firstBad = el;
  }
  if (!songFile.files[0]) fileDrop.classList.add("invalid"); else fileDrop.classList.remove("invalid");
  if (firstBad) { showResult(addResult, "err", 400, { msg: "Title and artist are required." }); firstBad.focus(); return; }
  if (!songFile.files[0]) { showResult(addResult, "err", 400, { msg: "Choose a .wav file to index." }); return; }

  addButton.disabled = true;
  showResult(addResult, "scan", 202, { title: "Indexing track…", msg: "Running the fingerprint pipeline." });
  try {
    const { ok, status, data } = await postAudio("/api/songs", songFile.files[0], {
      title: titleInput.value, artist: artistInput.value,
    });
    if (!ok) { showResult(addResult, "err", status, { msg: data.error || "Could not index that file." }); return; }
    showResult(addResult, "ok", 200, {
      label: "indexed",
      title: `Added as ID ${String(data.song_id).padStart(3, "0")}`,
      stats: data.stats, notes: data.notes,
    });
    addForm.reset();
    songFileName.textContent = "Choose a .wav file";
    fileDrop.classList.remove("filled");
    refreshSongs();
  } catch (err) {
    showResult(addResult, "err", 500, { msg: err.message });
  } finally {
    addButton.disabled = false;
  }
});

[titleInput, artistInput].forEach((el) =>
  el.addEventListener("input", () => el.classList.remove("invalid")));

refreshSongs();
