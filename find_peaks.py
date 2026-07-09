import numpy as np


def find_peaks(spectrogram, *, neighborhood_rank=2, neighborhood_iterations=20, amp_min_percentile=75):
    """Extract local peaks from a log-scaled spectrogram.

    Parameters
    ----------
    spectrogram : np.ndarray
        2-D array of log-scaled amplitudes, shape (num_freqs, num_times)
        (from create_spectrogram)
    neighborhood_rank : int, keyword-only
        Connectivity of the base neighborhood footprint (default 2)
    neighborhood_iterations : int, keyword-only
        Number of times the footprint is iterated/grown; larger means
        fewer, more spread-out peaks (default 20)
    amp_min_percentile : float, keyword-only
        Peaks with log-amplitude below this percentile of the
        spectrogram are discarded (default 75)

    Returns
    -------
    peaks : list[tuple[int, int]]
        List of (freq_index, time_index) locations of local peaks,
        sorted by time_index (column) in ascending order.
        freq_index/time_index are row/column indices into the
        spectrogram -- use the freqs/times arrays from
        create_spectrogram to convert to Hz/seconds if needed.
    """
    pass
