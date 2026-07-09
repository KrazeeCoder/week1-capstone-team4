import numpy as np
from scipy.io import wavfile


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
    return data.astype(np.float64), rate