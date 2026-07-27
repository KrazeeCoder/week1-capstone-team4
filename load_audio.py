import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly


def standardize_rate(data, rate, target_rate):
    """Casts to float64 and resamples to target_rate if needed.

    resample_poly silently returns all-zeros on integer PCM input in this
    scipy build, so data must already be float before resampling -- shared
    here so every audio source (file, mic recording) gets the fix once.
    """
    data = np.asarray(data, dtype=np.float64)
    if rate != target_rate:
        data = resample_poly(data, target_rate, rate)
        rate = target_rate
    return data, rate


def load_audio(source, *, mic_duration=None, mic_sample_rate=44100):
    if source == "mic":
        if mic_duration is None:
            raise ValueError("You need a mic duration bro")
        import pyaudio
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=mic_sample_rate,
            input=True,
            frames_per_buffer=1024,
        )
        frames = []
        num_chunks = int(mic_sample_rate / 1024 * mic_duration)
        for i in range(num_chunks):
            frames.append(stream.read(1024))
        stream.stop_stream()
        stream.close()
        p.terminate()
        samples = np.frombuffer(b"".join(frames), dtype=np.int16).astype(np.float64)
        return samples, mic_sample_rate

    rate, data = wavfile.read(source)
    if data.ndim == 2:
        data = data[:, 0]

    if rate != mic_sample_rate:
        print(f"Fixing sample rate: {rate}Hz -> {mic_sample_rate}Hz")
    return standardize_rate(data, rate, mic_sample_rate)
