"""Shared helpers for the retrieval/reranking evaluation scripts.

Keeps the "clip -> spectrogram -> peaks -> fingerprints -> query" path in one
place so evaluate_retrieval.py, evaluate_robustness.py, and the topological
reranker all exercise the exact same Stage-1 pipeline as main.py.
"""
from create_spectogram import create_spectrogram
from find_peaks import find_peaks
from create_fingerprints import peaks_to_fingerprints


def query_clip(samples, rate, db, k=10):
    """Runs the Stage-1 fingerprint pipeline on a clip and queries db.

    Returns the raw query result dict: {"best_matches", "ranked", "offsets"}.
    `ranked` contains *every* song_id that shares at least one fingerprint
    hash with the clip, best score first -- not just the top k -- so rank_of
    below can distinguish "never retrieved" from "retrieved but ranked low".
    """
    spectrogram, _, _ = create_spectrogram(samples, rate)
    peaks = find_peaks(spectrogram)
    fingerprints = peaks_to_fingerprints(peaks)
    result = db.query(fingerprints, k=k)
    return result


def rank_of(result, true_song_id):
    """1-based rank of true_song_id in result["ranked"], or None if the song
    never shared a single fingerprint hash with the query clip at all
    (a pure retrieval failure, as opposed to a ranking failure).
    """
    for idx, (song_id, _score) in enumerate(result["ranked"]):
        if song_id == true_song_id:
            return idx + 1
    return None


def classify(rank, k_values=(1, 5, 10)):
    """Buckets a rank into one outcome string for reporting."""
    if rank is None:
        return "retrieval_failure"
    for k in k_values:
        if rank <= k:
            return f"top_{k}"
    return "ranking_failure"
