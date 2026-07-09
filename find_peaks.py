import numpy as np


def find_peaks(spectrogram, *, neighborhood_iterations=20, amp_min_percentile=75):
    pass

# Note:
# spectrogram: 2D log-scaled amplitudes from create_spectrogram
# returns: peaks: list of (freq_index, time_index) tuples, sorted by time_index
