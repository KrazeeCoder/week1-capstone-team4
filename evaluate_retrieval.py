"""Phase 0 baseline: for clean (unmodified) short clips, how often is the
correct song retrieved at all, and how often does it land in the top-1/5/10?

This is the retrieval-vs-ranking diagnostic from the capstone proposal,
measured before any pitch/tempo modification is applied. Run
evaluate_robustness.py for the modified-audio sweep (Phase 1).
"""
import argparse
from collections import Counter

import numpy as np

from database import AudioDatabase
from load_audio import load_audio
from random_clips import make_random_clip
from eval_utils import query_clip, rank_of, classify

K_VALUES = (1, 5, 10)


def evaluate(db_path="eval_data.pkl", clip_lengths=(5, 10, 20), clips_per_song=3, seed=0):
    db = AudioDatabase(db_path)
    db.load_data()
    if not db.metadata:
        raise SystemExit(f"{db_path} has no songs -- run build_eval_database.py first.")

    rng = np.random.default_rng(seed)
    outcomes_by_length = {length: Counter() for length in clip_lengths}
    rows = []

    for song_id, info in db.metadata.items():
        try:
            samples, rate = load_audio(info["filename"])
        except FileNotFoundError:
            print(f"skip: file not found for '{info['title']}'")
            continue

        for length in clip_lengths:
            for _ in range(clips_per_song):
                clip = make_random_clip(samples, length, rate, rng)
                result = query_clip(clip, rate, db, k=max(K_VALUES))
                rank = rank_of(result, song_id)
                outcome = classify(rank, K_VALUES)
                outcomes_by_length[length][outcome] += 1
                rows.append((info["title"], length, rank, outcome))

    print(f"\n{'Title':<45} | {'len(s)':>6} | {'rank':>5} | outcome")
    print("-" * 85)
    for title, length, rank, outcome in rows:
        print(f"{title[:45]:<45} | {length:>6} | {str(rank):>5} | {outcome}")

    print("\n=== Summary (Phase 0: clean clips, no pitch/tempo modification) ===")
    for length in clip_lengths:
        counts = outcomes_by_length[length]
        total = sum(counts.values())
        print(f"\nClip length {length}s (n={total}):")
        cumulative = 0
        for k in K_VALUES:
            cumulative += sum(v for outcome, v in counts.items() if outcome == f"top_{k}") if k == K_VALUES[0] else 0
        running = 0
        for k in K_VALUES:
            running += counts[f"top_{k}"]
            print(f"  recall@{k:<2} = {running / total:.1%}")
        print(f"  ranking_failure (retrieved but outside top_{K_VALUES[-1]}) = {counts['ranking_failure'] / total:.1%}")
        print(f"  retrieval_failure (never a single hash hit)      = {counts['retrieval_failure'] / total:.1%}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="eval_data.pkl")
    parser.add_argument("--clips-per-song", type=int, default=3)
    args = parser.parse_args()
    evaluate(db_path=args.db, clips_per_song=args.clips_per_song)
