"""Phase 1: sweep pitch-shift and time-stretch modifications (Panako-style)
over short clips and measure how Stage-1 recall@1/5/10 degrades.

This reproduces the "characteristic dip" Panako reports, but on our own
smaller DB, and is the evidence for *why* a pitch/tempo-invariant reranker
(Stage 2) is needed.
"""
import argparse
from collections import Counter, defaultdict

import librosa
import numpy as np

from database import AudioDatabase
from load_audio import load_audio
from random_clips import make_random_clip
from eval_utils import query_clip, rank_of, classify

K_VALUES = (1, 5, 10)

PITCH_SHIFTS_SEMITONES = [-4, -2, -1, 0, 1, 2, 4]
TIME_STRETCH_RATES = [0.84, 0.92, 1.0, 1.08, 1.16]  # >1.0 = faster/shorter


def apply_pitch_shift(clip, rate, semitones):
    if semitones == 0:
        return clip
    return librosa.effects.pitch_shift(y=clip, sr=rate, n_steps=semitones)


def apply_time_stretch(clip, rate_factor):
    if rate_factor == 1.0:
        return clip
    return librosa.effects.time_stretch(y=clip, rate=rate_factor)


def run_sweep(db_path, clip_length, clips_per_song, seed, mode):
    db = AudioDatabase(db_path)
    db.load_data()
    if not db.metadata:
        raise SystemExit(f"{db_path} has no songs -- run build_eval_database.py first.")

    rng = np.random.default_rng(seed)
    sweep_values = PITCH_SHIFTS_SEMITONES if mode == "pitch" else TIME_STRETCH_RATES
    outcomes = {v: Counter() for v in sweep_values}

    songs = list(db.metadata.items())
    for song_id, info in songs:
        try:
            samples, rate = load_audio(info["filename"])
        except FileNotFoundError:
            print(f"skip: file not found for '{info['title']}'")
            continue

        for _ in range(clips_per_song):
            clip = make_random_clip(samples, clip_length, rate, rng).astype(np.float32)
            for value in sweep_values:
                if mode == "pitch":
                    modified = apply_pitch_shift(clip, rate, value)
                else:
                    modified = apply_time_stretch(clip, value)

                result = query_clip(modified, rate, db, k=max(K_VALUES))
                rank = rank_of(result, song_id)
                outcomes[value][classify(rank, K_VALUES)] += 1

    label = "semitone shift" if mode == "pitch" else "time-stretch rate"
    print(f"\n=== Phase 1: {label} sweep, clip_length={clip_length}s, db={db_path} ===")
    print(f"{'value':>10} | " + " | ".join(f"recall@{k:<3}" for k in K_VALUES) + " | ranking_fail | retrieval_fail")
    for value in sweep_values:
        counts = outcomes[value]
        total = sum(counts.values())
        if total == 0:
            continue
        running = 0
        recalls = []
        for k in K_VALUES:
            running += counts[f"top_{k}"]
            recalls.append(running / total)
        recall_str = " | ".join(f"{r:>9.1%}" for r in recalls)
        print(
            f"{value:>10} | {recall_str} | "
            f"{counts['ranking_failure'] / total:>12.1%} | "
            f"{counts['retrieval_failure'] / total:>14.1%}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="eval_data.pkl")
    parser.add_argument("--clip-length", type=float, default=10)
    parser.add_argument("--clips-per-song", type=int, default=2)
    parser.add_argument("--mode", choices=["pitch", "tempo"], default="pitch")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    run_sweep(args.db, args.clip_length, args.clips_per_song, args.seed, args.mode)
