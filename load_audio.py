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
