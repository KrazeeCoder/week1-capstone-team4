import numpy as np


def create_spectrogram(samples, sample_rate, *, window_size=4096, overlap=0.5):
    pass

# Note:
# samples, sample_rate: output of load_audio
# returns: (spectrogram: np.ndarray, freqs: np.ndarray, times: np.ndarray)
# spectrogram is 2D log-scaled amplitudes, shape (num_freqs, num_times)
