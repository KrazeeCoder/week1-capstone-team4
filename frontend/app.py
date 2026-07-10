"""Web frontend for the audio fingerprinting capstone.

Run from the repo root (or anywhere):
    python frontend/app.py
Then open http://localhost:5000 in your browser.

The server wires the browser UI to the team's Python pipeline
(load_audio -> create_spectrogram -> find_peaks -> fingerprints -> match).
Pipeline stages that aren't implemented yet are reported gracefully
instead of crashing, so this keeps working as teammates fill them in.
"""

import os
import sys
import tempfile
import traceback

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from flask import Flask, jsonify, request, send_from_directory

from load_audio import load_audio
from create_spectogram import create_spectrogram
from find_peaks import find_peaks
import database

SONGS_DIR = os.path.join(REPO_ROOT, "songs")
os.makedirs(SONGS_DIR, exist_ok=True)

app = Flask(__name__)


def _make_database():
    """Create an AudioDatabase, tolerating both old and new constructors."""
    try:
        return database.AudioDatabase()
    except TypeError:
        return database.AudioDatabase({})


db = _make_database()


def _list_songs():
    """Return [{song_id, title, artist, filename}] from whatever the db supports."""
    songs = []
    metadata = getattr(db, "metadata", None)
    if isinstance(metadata, dict):
        for song_id, info in metadata.items():
            songs.append({
                "song_id": song_id,
                "title": info.get("title", "?"),
                "artist": info.get("artist", "?"),
                "filename": info.get("filename", ""),
            })
    return songs


def _fingerprint_peaks(peaks):
    """Try the team's fingerprint function; return (fingerprints, error_message)."""
    try:
        import create_fingerprints
    except Exception as exc:
        return None, f"create_fingerprints could not be imported: {exc}"
    for name in ("create_fingerprints", "make_fingerprints", "fingerprint"):
        func = getattr(create_fingerprints, name, None)
        if callable(func):
            return func(peaks), None
    return None, "create_fingerprints.py has no fingerprint function yet"


def _run_pipeline(wav_path):
    """Run audio through the pipeline as far as it's implemented."""
    samples, sample_rate = load_audio(wav_path)
    spectrogram, freqs, times = create_spectrogram(samples, sample_rate)
    peaks = find_peaks(spectrogram)
    result = {
        "duration_seconds": round(len(samples) / sample_rate, 2),
        "sample_rate": int(sample_rate),
        "num_peaks": len(peaks),
        "peaks_xy": _sample_peaks(peaks, spectrogram.shape),
    }
    fingerprints, fp_error = _fingerprint_peaks(peaks)
    return result, fingerprints, fp_error


def _sample_peaks(peaks, shape, limit=150):
    """Downsample peaks to normalized [time, freq] points for the constellation view."""
    if not peaks:
        return []
    n_freqs, n_times = shape
    step = max(1, len(peaks) // limit)
    sampled = peaks[::step][:limit]
    fx = max(1, n_freqs - 1)
    tx = max(1, n_times - 1)
    return [[round(t / tx, 4), round(f / fx, 4)] for (f, t) in sampled]


def _save_upload(file_storage, directory):
    filename = os.path.basename(file_storage.filename or "clip.wav")
    if not filename.lower().endswith(".wav"):
        filename += ".wav"
    path = os.path.join(directory, filename)
    file_storage.save(path)
    return path


@app.get("/")
def index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "index.html")


@app.get("/<path:name>")
def static_files(name):
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), name)


@app.get("/api/songs")
def api_list_songs():
    return jsonify({"songs": _list_songs()})


@app.post("/api/songs")
def api_add_song():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file was uploaded."}), 400
    title = (request.form.get("title") or "").strip()
    artist = (request.form.get("artist") or "").strip()
    if not title or not artist:
        return jsonify({"error": "Both a title and an artist are required."}), 400
    try:
        wav_path = _save_upload(request.files["audio"], SONGS_DIR)
        stats, fingerprints, fp_error = _run_pipeline(wav_path)
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Could not process that file. Is it a valid .wav?"}), 400

    add_song = getattr(db, "add_song", None)
    if not callable(add_song):
        return jsonify({
            "error": "This branch's database.py doesn't support song metadata yet "
                     "(merge the latest main to get it).",
        }), 501
    song_id = add_song(title, artist, os.path.basename(wav_path))

    notes = []
    if fingerprints is not None and callable(getattr(db, "store_fingerprints", None)):
        db.store_fingerprints(song_id, fingerprints)
        if not getattr(db, "fingerprints", True):
            notes.append("store_fingerprints() is still a stub, so nothing was stored.")
    else:
        notes.append(fp_error or "Fingerprint storage isn't implemented yet.")

    save_data = getattr(db, "save_data", None)
    if callable(save_data):
        try:
            save_data()
        except Exception:
            notes.append("Warning: saving the database to disk failed.")

    return jsonify({"song_id": song_id, "stats": stats, "notes": notes})


@app.post("/api/match")
def api_match():
    if "audio" not in request.files:
        return jsonify({"error": "No audio was uploaded."}), 400
    try:
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = _save_upload(request.files["audio"], tmp)
            stats, fingerprints, fp_error = _run_pipeline(wav_path)
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Could not process that audio. Is it a valid .wav?"}), 400

    if fingerprints is None:
        return jsonify({
            "match": None,
            "stats": stats,
            "message": "The clip was analyzed (spectrogram + peaks work!), but matching "
                       f"isn't possible yet: {fp_error}",
        })

    query = getattr(db, "query", None)
    if not callable(query):
        return jsonify({
            "match": None,
            "stats": stats,
            "message": "Fingerprints were made, but the database has no query() yet.",
        })
    try:
        match = query(fingerprints)
    except Exception:
        traceback.print_exc()
        return jsonify({
            "match": None,
            "stats": stats,
            "message": "query() raised an error — it's probably still in progress.",
        })
    if match is None:
        return jsonify({
            "match": None,
            "stats": stats,
            "message": "No match found (or query() is still a stub returning None).",
        })
    return jsonify({"match": str(match), "stats": stats})


if __name__ == "__main__":
    print("Open http://localhost:5000 in your browser")
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
