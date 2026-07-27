import numpy as np
from numba import njit
from scipy.ndimage import generate_binary_structure, iterate_structure


@njit
def _local_peaks(data, rows, cols, amp_min):
    peaks = []
    for c in range(data.shape[1]):
        for r in range(data.shape[0]):
            if data[r, c] <= amp_min:
                continue
            is_peak = True
            for i in range(len(rows)):
                dr = rows[i]
                dc = cols[i]
                if dr == 0 and dc == 0:
                    continue
                nr = r + dr
                nc = c + dc
                if nr < 0 or nr >= data.shape[0] or nc < 0 or nc >= data.shape[1]:
                    continue
                if data[r, c] < data[nr, nc]:
                    is_peak = False
                    break
            if is_peak:
                peaks.append((r, c))
    return peaks


def find_peaks(spectrogram, *, neighborhood_iterations=20, amp_min_percentile=60):
    footprint = iterate_structure(generate_binary_structure(2, 1), neighborhood_iterations)
    rows, cols = np.nonzero(footprint)
    rows = rows - footprint.shape[0] // 2
    cols = cols - footprint.shape[1] // 2
    amp_min = np.percentile(spectrogram, amp_min_percentile)
    peaks = [(int(r), int(c)) for r, c in _local_peaks(spectrogram, rows, cols, amp_min)]
    peaks.sort(key=lambda p: p[1])
    return peaks

# Note:
# spectrogram: 2D log-scaled amplitudes from create_spectrogram
# returns: peaks: list of (freq_index, time_index) tuples, sorted by time_index
