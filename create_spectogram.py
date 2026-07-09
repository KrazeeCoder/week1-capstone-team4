import numpy as np


def create_spectrogram(samples, sample_rate, *, window_size=4096, overlap=0.5):
    """Convert digital audio samples into a spectrogram of log-scaled amplitudes.

    Parameters
    ----------
    samples : np.ndarray
        1-D array of audio samples (from load_audio)
    sample_rate : int
        Sampling rate of the recording, in Hz (from load_audio)
    window_size : int, keyword-only
        Number of samples per FFT window (default 4096)
    overlap : float, keyword-only
        Fraction of window overlap between adjacent windows (default 0.5)

    Returns
    -------
    (spectrogram: np.ndarray, freqs: np.ndarray, times: np.ndarray)
        spectrogram : 2-D array, shape (num_freqs, num_times), of
            log-scaled amplitudes (log applied after clipping values
            below 1e-20 to avoid log(0))
        freqs : 1-D array, frequency (Hz) of each row
        times : 1-D array, time (sec) of each column
    """
    pass
