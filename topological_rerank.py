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
    if len(samples) < rate * 1:
        return None
    chroma = librosa.feature.chroma_cqt(
        y=np.asarray(samples, dtype=np.float32), sr=rate, hop_length=CHROMA_HOP
    )
    if chroma.shape[1] < 2:
        return None
#Chroma collapses all freqs into 12 bins, one pitch/class
#Pitch class is more robust to small pitch shifts than raw frequency.
#Output(12, num_time_frames), each column is a time slice.
    t_old = np.linspace(0.0, 1.0, chroma.shape[1])
    t_new = np.linspace(0.0, 1.0, n_frames)
    points = np.stack([np.interp(t_new, t_old, chroma[bin_idx]) for bin_idx in range(chroma.shape[0])], axis=1)
#Resamples both onto the same 40 point timeline regardless of original duration, so that the MST is always 39 edges and the signature is always 39 death times.
    dists = squareform(pdist(points))
    mst = minimum_spanning_tree(dists)
    death_times = np.sort(mst.data)
#Essentially, what the min spanning tree data structure does is store the edges of the tree in a 1D array, sorted by weight. 
#The weight of each edge is the distance between two points in the chroma space. The death times are the weights of the edges 
# in the minimum spanning tree, which represent the "lifetimes" of the features in the topological signature. 
# The number of death times should be equal to n_frames - 1, 
# since a minimum spanning tree for n points has n - 1 edges. If this condition is not met, 
# it indicates that something went wrong in the computation, and we return None.
#This is motivated by persistent homology: imagine growing a ball of radius r
#around each of the 40 points, r increasing from 0. At r=0 every point is its own
#cluster (40 components). As r grows, two points' balls touch once r reaches half
#their distance apart, and their clusters merge -- one component "dies" at that r.
#The sorted list of all these merge-radii IS the persistence diagram (birth=0 for
#every point, death=the radius it merged at). That sorted list of merge-radii is
#exactly the sorted edge weights of the minimum spanning tree (a known equivalence:
#single-linkage clustering merge heights = MST edge weights). So instead of
#simulating the growing radius, we just build the MST directly and sort its edges 
#same answer, far cheaper.

    if len(death_times) != n_frames - 1:
        return None
    return death_times
#Small correction to how this is usually phrased: the signature isn't "isometric to"
#the chroma representation -- it's a lossy summary (many different point clouds can
#produce the same sorted death-times). What's actually true, and what buys pitch-shift
#invariance: the signature only depends on PAIRWISE DISTANCES between the 40 points,
#and a uniform pitch shift permutes all 12 chroma-bin coordinates the same way for
#every point. Permuting coordinates identically for every point is an isometry of the
#point cloud (it doesn't change any distance between any two points), so the MST edge
#weights -- and therefore the signature -- come out identical before and after a
#uniform pitch shift. It's invariant TO an isometry, not isometric itself.

def topo_distance(sig_a, sig_b):
    return float(np.linalg.norm(sig_a - sig_b))
#compares two signatures by computing the Euclidean distance between their death times.
#We don't need to use a more sophisticated distance metric because the topological signature 
# is already a compact representation of the original chroma features, and 
# the Euclidean distance is sufficient to capture the differences between them.

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
