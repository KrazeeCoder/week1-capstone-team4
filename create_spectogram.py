import numpy as np
import matplotlib.mlab as mlab


def spectrogram_hop_length(window_size=4096, overlap=0.5):
    """Samples between consecutive spectrogram columns -- lets callers convert
    a fingerprint anchor-time offset (in spectrogram columns) back to seconds.
    """
    return window_size - int(window_size * overlap)


def create_spectrogram(samples, sample_rate, *, window_size=4096, overlap=0.5):
    spectrogram, freqs, times = mlab.specgram(
        samples,
        NFFT=window_size,
        Fs=sample_rate,
        window=mlab.window_hanning,
        noverlap=int(window_size * overlap),
    )
    spectrogram = np.log(np.clip(spectrogram, 1e-20, None))
    return spectrogram, freqs, times

# Note:
# samples, sample_rate: output of load_audio
# returns: (spectrogram: np.ndarray, freqs: np.ndarray, times: np.ndarray)
# spectrogram is 2D log-scaled amplitudes, shape (num_freqs, num_times)
