// Song Finder — talks to the Flask API (/api/match, /api/songs)

// ---- turn recorded mic samples into a .wav file ----
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
  return stats.num_peaks + " peaks, " + stats.duration_seconds + "s, " + stats.sample_rate + " Hz";
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}

// ---- identify a clip (used by both the mic and the upload box) ----
const matchResult = document.getElementById("match-result");

async function identify(blob) {
  matchResult.textContent = "Analyzing...";
  try {
    const { ok, status, data } = await postAudio("/api/match", blob);
    if (!ok) { matchResult.textContent = "Error: " + (data.error || status); return; }
    let text;
    if (data.match) text = "Match found: " + data.match;
    else text = data.message || "No match found.";
    if (data.stats) text += "  [" + statsText(data.stats) + "]";
    matchResult.textContent = text;
  } catch (err) {
    matchResult.textContent = "Error: " + err.message;
  }
}

// ---- microphone: tap to start, tap to stop ----
const scanBtn = document.getElementById("scan-btn");
const scanText = document.getElementById("scan-text");
let recording = null;

scanBtn.addEventListener("click", () => {
  if (recording) stopRecording();
  else startRecording();
});

async function startRecording() {
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    matchResult.textContent = "Microphone blocked. Allow mic access, or upload a .wav instead.";
    return;
  }
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const source = ctx.createMediaStreamSource(stream);
  const processor = ctx.createScriptProcessor(4096, 1, 1);
  const chunks = [];
  processor.onaudioprocess = (e) => chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
  source.connect(processor);
  processor.connect(ctx.destination);
  recording = { ctx, stream, source, processor, chunks };
  matchResult.textContent = "Recording... tap Stop when done.";
  scanText.textContent = "Stop recording";
}

async function stopRecording() {
  const r = recording;
  recording = null;
  scanText.textContent = "Start recording";
  r.processor.disconnect();
  r.source.disconnect();
  r.stream.getTracks().forEach((t) => t.stop());

  const total = r.chunks.reduce((n, c) => n + c.length, 0);
  if (!total) { await r.ctx.close(); matchResult.textContent = "Didn't catch any audio."; return; }
  const samples = new Float32Array(total);
  let pos = 0;
  for (const c of r.chunks) { samples.set(c, pos); pos += c.length; }
  const blob = encodeWav(samples, r.ctx.sampleRate);
  await r.ctx.close();
  identify(blob);
}

// ---- upload a clip to identify ----
document.getElementById("clip-file").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file) identify(file);
  e.target.value = "";
});

// ---- library list ----
const songsList = document.getElementById("songs-list");

async function refreshSongs() {
  try {
    const resp = await fetch("/api/songs");
    const data = await resp.json();
    if (!data.songs || !data.songs.length) {
      songsList.innerHTML = "<li>No songs yet. Add one below.</li>";
      return;
    }
    songsList.innerHTML = data.songs.map((s) =>
      "<li>#" + escapeHtml(String(s.song_id)) + " - " + escapeHtml(s.title) +
      " by " + escapeHtml(s.artist) + " (" + escapeHtml(s.filename) + ")</li>"
    ).join("");
  } catch {
    songsList.innerHTML = "<li>Can't reach the server.</li>";
  }
}

// ---- add a song ----
const addForm = document.getElementById("add-form");
const addButton = document.getElementById("add-button");
const addResult = document.getElementById("add-result");
const titleInput = document.getElementById("song-title");
const artistInput = document.getElementById("song-artist");
const songFile = document.getElementById("song-file");

addForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!titleInput.value.trim() || !artistInput.value.trim()) {
    addResult.textContent = "Title and artist are required.";
    return;
  }
  if (!songFile.files[0]) {
    addResult.textContent = "Choose a .wav file.";
    return;
  }
  addButton.disabled = true;
  addResult.textContent = "Adding...";
  try {
    const { ok, status, data } = await postAudio("/api/songs", songFile.files[0], {
      title: titleInput.value, artist: artistInput.value,
    });
    if (!ok) { addResult.textContent = "Error: " + (data.error || status); return; }
    let text = "Added as #" + data.song_id + ".";
    if (data.stats) text += "  [" + statsText(data.stats) + "]";
    if (data.notes && data.notes.length) text += "  Notes: " + data.notes.join("; ");
    addResult.textContent = text;
    addForm.reset();
    refreshSongs();
  } catch (err) {
    addResult.textContent = "Error: " + err.message;
  } finally {
    addButton.disabled = false;
  }
});

refreshSongs();
