from load_audio import load_audio
from create_spectogram import create_spectrogram
from find_peaks import find_peaks
from create_fingerprints import peaks_to_fingerprints
wav_path = input("Enter the path to the WAV file: ")
samples, rate = load_audio(wav_path)
spectrogram, freqs, times = create_spectrogram(samples, rate)
peaks = find_peaks(spectrogram)
fingerprints = peaks_to_fingerprints(peaks)
#print("rate:", rate)
#print("samples:", len(samples))
#print("spectrogram shape:", spectrogram.shape)
#print("peaks:", len(peaks))
#print("fingerprints:", len(fingerprints))
