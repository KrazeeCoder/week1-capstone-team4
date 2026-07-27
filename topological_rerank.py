"""Phase 2: topological reranker for the top-N candidates Stage 1 retrieves.

Method (0-dimensional persistent homology over chroma-CQT):
  1. Take a chroma-CQT frame sequence for the query clip and for the aligned
     window of each Stage-1 candidate (alignment comes from the offset
     Stage 1 already computed from its hash-tally voting).
  2. Time-normalize both sequences to a fixed number of frames -- this
     cancels a uniform linear time-stretch, the same invariance Panako gets
     from its time-difference-ratio hash.
  3. Treat each normalized sequence as a point cloud (one 12-dim point per
     frame) and compute its 0-dim persistence diagram via single-linkage
     clustering (the minimum-spanning-tree edge weights = H0 death times).
     A uniform pitch shift permutes chroma-bin coordinates identically for
     every frame, which is an isometry of this point cloud -- so the H0
     signature is pitch-shift invariant *by construction*, not just
     empirically, for integer semitone shifts (fractional shifts smear
     across neighboring bins, so the invariance degrades gracefully).
  4. Rerank the Stage-1 candidates by L2 distance between persistence
     signatures (ascending = more similar).

This is a lightweight, dependency-free stand-in for full Vietoris-Rips
persistent homology -- accurate for H0, and sufficient to test whether
reranking recovers songs Stage-1 ranked below #1.
"""
import numpy as np
import librosa
from scipy.spatial.distance import pdist, squareform
from scipy.sparse.csgraph import minimum_spanning_tree

from create_spectogram import spectrogram_hop_length
from load_audio import load_audio

N_FRAMES = 40
CHROMA_HOP = 1024
MIN_WINDOW_SECONDS = 3


def chroma_signature(samples, rate, n_frames=N_FRAMES):
    """Returns a length-(n_frames - 1) sorted array of H0 death times, or
    None if the clip is too short to build a meaningful point cloud.
    """
    if len(samples) < rate * 1:
        return None
    chroma = librosa.feature.chroma_cqt(
        y=np.asarray(samples, dtype=np.float32), sr=rate, hop_length=CHROMA_HOP
    )
    if chroma.shape[1] < 2:
        return None

    t_old = np.linspace(0.0, 1.0, chroma.shape[1])
    t_new = np.linspace(0.0, 1.0, n_frames)
    points = np.stack([np.interp(t_new, t_old, chroma[bin_idx]) for bin_idx in range(chroma.shape[0])], axis=1)

    dists = squareform(pdist(points))
    mst = minimum_spanning_tree(dists)
    death_times = np.sort(mst.data)
    if len(death_times) != n_frames - 1:
        return None
    return death_times


def topo_distance(sig_a, sig_b):
    return float(np.linalg.norm(sig_a - sig_b))


def rerank_candidates(query_samples, rate, db, stage1_result, top_n=5, audio_cache=None, gate_ratio=1.5):
    """Reranks the top_n Stage-1 candidates using the topological signature.

    `audio_cache` is an optional {song_id: (samples, rate)} dict. Reranking
    needs the full candidate song to slice out the aligned window, and
    reloading + resampling multi-minute WAVs from disk for every clip is the
    dominant cost of batch evaluation -- callers that rerank many clips
    against the same DB should load each song once and pass the cache in.

    `gate_ratio`: skip reranking entirely when Stage 1's top hash-tally score
    already beats the runner-up by this ratio. Measured empirically: without
    a gate, the topological signature is noisy enough to demote roughly as
    many already-correct Stage-1 top-1 picks as it fixes ranking failures
    elsewhere (net lift near zero). Stage 1's tally score is a reasonable
    confidence proxy -- a landslide winner is rarely worth second-guessing,
    so only ambiguous cases get sent through the (expensive, noisier)
    topological comparison.

    Returns a list of (song_id, stage1_score) ordered by topological
    similarity, best first. Falls back to the original Stage-1 order for any
    candidate whose audio/window can't be turned into a signature, or when
    the gate above triggers.
    """
    ranked = stage1_result["ranked"][:top_n]
    if not ranked:
        return []

    if len(ranked) > 1 and ranked[0][1] >= gate_ratio * ranked[1][1]:
        return ranked

    offsets = stage1_result["offsets"]
    query_sig = chroma_signature(query_samples, rate)
    if query_sig is None:
        return ranked

    hop_length = spectrogram_hop_length()
    query_duration = max(len(query_samples) / rate, MIN_WINDOW_SECONDS)

    scored = []
    for rank_idx, (song_id, stage1_score) in enumerate(ranked):
        if audio_cache is not None and song_id in audio_cache:
            song_samples, song_rate = audio_cache[song_id]
        else:
            info = db.metadata[song_id]
            try:
                song_samples, song_rate = load_audio(info["filename"])
            except FileNotFoundError:
                scored.append((song_id, stage1_score, float("inf"), rank_idx))
                continue
            if audio_cache is not None:
                audio_cache[song_id] = (song_samples, song_rate)

        offset_frames = offsets.get(song_id, 0)
        offset_seconds = offset_frames * hop_length / rate
        start_sample = max(0, int(round(offset_seconds * song_rate)))
        end_sample = min(len(song_samples), start_sample + int(round(query_duration * song_rate)))
        window = song_samples[start_sample:end_sample]

        cand_sig = chroma_signature(window, song_rate)
        if cand_sig is None:
            distance = float("inf")
        else:
            distance = topo_distance(query_sig, cand_sig)
        scored.append((song_id, stage1_score, distance, rank_idx))

    # ties (e.g. both inf) keep Stage-1 order via rank_idx
    scored.sort(key=lambda item: (item[2], item[3]))
    return [(song_id, stage1_score) for song_id, stage1_score, _distance, _rank_idx in scored]
