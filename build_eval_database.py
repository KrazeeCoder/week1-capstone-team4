"""Builds a larger fingerprint database (eval_data.pkl) from every WAV file in
AUDIO_DIR, so retrieval-vs-ranking evaluation (recall@1/5/10) is meaningful.
data.pkl (the 5-song production DB) is left untouched.
"""
import os
import time

from load_audio import load_audio
from create_spectogram import create_spectrogram
from find_peaks import find_peaks
from create_fingerprints import peaks_to_fingerprints
from database import AudioDatabase

AUDIO_DIR = r"C:\Users\palsh\Downloads\WAV Files for Audio Capstone\WAV Files for Audio Capstone"
EVAL_DB_PATH = "eval_data.pkl"


def title_artist_from_filename(filename):
    stem = os.path.splitext(filename)[0]
    stem = stem.rsplit(" [", 1)[0]  # drop the trailing YouTube ID
    if " - " in stem:
        artist, title = stem.split(" - ", 1)
    else:
        artist, title = "Unknown", stem
    return title.strip(), artist.strip()


def build():
    db = AudioDatabase(EVAL_DB_PATH)
    wav_files = sorted(f for f in os.listdir(AUDIO_DIR) if f.lower().endswith(".wav"))
    print(f"Found {len(wav_files)} WAV files in {AUDIO_DIR}")

    for i, filename in enumerate(wav_files):
        path = os.path.join(AUDIO_DIR, filename)
        title, artist = title_artist_from_filename(filename)
        t0 = time.time()
        samples, rate = load_audio(path)
        spectrogram, _, _ = create_spectrogram(samples, rate)
        peaks = find_peaks(spectrogram)
        fingerprints = peaks_to_fingerprints(peaks)
        song_id = db.add_song(title, artist, path)
        db.store_fingerprints(song_id, fingerprints)
        print(
            f"[{i + 1}/{len(wav_files)}] '{title}' by {artist}: "
            f"{len(peaks)} peaks, {len(fingerprints)} fingerprints "
            f"({time.time() - t0:.1f}s)"
        )

    db.save_data()
    print(f"Saved {len(wav_files)} songs to {EVAL_DB_PATH}")


if __name__ == "__main__":
    build()
