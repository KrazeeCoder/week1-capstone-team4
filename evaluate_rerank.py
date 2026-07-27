"""Phase 3: does topological reranking recover songs Stage 1 ranked below #1?

For each pitch-shifted clip:
  - retrieval_failure       -- true song never got a single hash hit; rerank can't help.
  - ranking_failure_deep    -- true song retrieved but outside the reranked top_n window.
  - already_top1            -- Stage 1 alone already got it right.
  - rerank_fixed            -- Stage 1 rank > 1 (within top_n), rerank moved it to #1.
  - rerank_no_help          -- Stage 1 rank > 1 (within top_n), rerank did NOT fix it.

This is the three-way outcome split (retrieval vs. ranking vs. rerank lift)
called out in the capstone proposal.
"""
import argparse
from collections import Counter

import numpy as np

from database import AudioDatabase
from load_audio import load_audio
from random_clips import make_random_clip
from eval_utils import query_clip, rank_of, LRUAudioCache
from topological_rerank import rerank_candidates

PITCH_SHIFTS_SEMITONES = [-4, -2, -1, 0, 1, 2, 4]
TOP_N_FOR_RERANK = 5


def classify_rerank(stage1_rank, rerank_rank, top_n):
    if stage1_rank is None:
        return "retrieval_failure"
    if stage1_rank > top_n:
        return "ranking_failure_deep"
    if stage1_rank == 1:
        return "already_top1"
    if rerank_rank == 1:
        return "rerank_fixed"
    return "rerank_no_help"


def run(db_path, clip_length, clips_per_song, seed, top_n, cache_capacity, max_songs, gate_ratio):
    import librosa

    db = AudioDatabase(db_path)
    db.load_data()
    if not db.metadata:
        raise SystemExit(f"{db_path} has no songs -- run build_eval_database.py first.")

    rng = np.random.default_rng(seed)
    outcomes = {shift: Counter() for shift in PITCH_SHIFTS_SEMITONES}
    stage1_top1 = {shift: 0 for shift in PITCH_SHIFTS_SEMITONES}
    rerank_top1 = {shift: 0 for shift in PITCH_SHIFTS_SEMITONES}
    totals = {shift: 0 for shift in PITCH_SHIFTS_SEMITONES}

    # Bounded LRU cache (float32) instead of preloading everything -- this
    # dataset is ~106 minutes of audio (~2GB as float64), too much to hold
    # resident at once on a machine with limited free RAM.
    audio_cache = LRUAudioCache(load_audio, capacity=cache_capacity)

    songs = list(db.metadata.items())
    if max_songs:
        songs = songs[:max_songs]

    for song_id, info in songs:
        try:
            samples, rate = audio_cache.get_or_load(song_id, info["filename"])
        except FileNotFoundError:
            print(f"skip: file not found for '{info['title']}'")
            continue

        for _ in range(clips_per_song):
            clip = make_random_clip(samples, clip_length, rate, rng).astype(np.float32)
            for shift in PITCH_SHIFTS_SEMITONES:
                modified = clip if shift == 0 else librosa.effects.pitch_shift(y=clip, sr=rate, n_steps=shift)

                stage1_result = query_clip(modified, rate, db, k=max(10, top_n))
                stage1_rank = rank_of(stage1_result, song_id)

                reranked = rerank_candidates(
                    modified, rate, db, stage1_result, top_n=top_n, audio_cache=audio_cache, gate_ratio=gate_ratio
                )
                rerank_rank = None
                for idx, (candidate_id, _score) in enumerate(reranked):
                    if candidate_id == song_id:
                        rerank_rank = idx + 1
                        break

                outcome = classify_rerank(stage1_rank, rerank_rank, top_n)
                outcomes[shift][outcome] += 1
                totals[shift] += 1
                stage1_top1[shift] += int(stage1_rank == 1)
                # if outside rerank window, rerank can't fix it -- report unchanged rank for top1 accounting
                effective_rank = rerank_rank if stage1_rank is not None and stage1_rank <= top_n else stage1_rank
                rerank_top1[shift] += int(effective_rank == 1)

    print(f"\n=== Phase 3: pitch-shift sweep with top-{top_n} topological rerank, clip_length={clip_length}s ===")
    header = f"{'shift':>6} | {'n':>4} | {'stage1@1':>9} | {'+rerank@1':>10} | " + \
             "already_top1 | rerank_fixed | rerank_no_help | ranking_fail_deep | retrieval_fail"
    print(header)
    for shift in PITCH_SHIFTS_SEMITONES:
        n = totals[shift]
        if n == 0:
            continue
        c = outcomes[shift]
        print(
            f"{shift:>6} | {n:>4} | {stage1_top1[shift] / n:>8.1%} | {rerank_top1[shift] / n:>9.1%} | "
            f"{c['already_top1']:>12} | {c['rerank_fixed']:>12} | {c['rerank_no_help']:>14} | "
            f"{c['ranking_failure_deep']:>17} | {c['retrieval_failure']:>14}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="eval_data.pkl")
    parser.add_argument("--clip-length", type=float, default=10)
    parser.add_argument("--clips-per-song", type=int, default=2)
    parser.add_argument("--top-n", type=int, default=TOP_N_FOR_RERANK)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--cache-capacity", type=int, default=6, help="max songs held resident in the audio LRU cache")
    parser.add_argument("--max-songs", type=int, default=None, help="limit how many DB songs are used as query sources")
    parser.add_argument("--gate-ratio", type=float, default=1.5, help="skip reranking when stage1 top score >= gate_ratio * runner-up")
    args = parser.parse_args()
    run(
        args.db, args.clip_length, args.clips_per_song, args.seed, args.top_n,
        args.cache_capacity, args.max_songs, args.gate_ratio,
    )
