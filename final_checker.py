from load_audio import load_audio
from create_spectogram import create_spectrogram
from find_peaks import find_peaks
from create_fingerprints import peaks_to_fingerprints

def identify_clip(samples, sample_rate, database):
    """
    Returns (song_title, artist) if a match is found, else None.
    """
    spectrogram, freqs, times = create_spectrogram(samples, sample_rate)
    peaks = find_peaks(spectrogram)
    fingerprints = peaks_to_fingerprints(peaks)

    result = database.query(fingerprints)

    if not matches:
        return None
    matches = result["best_matches"]
    
    best_song_id = max(matches, key=matches.get) 
    probability = matches[best_song_id]

    info = database.metadata[best_song_id]
    return info["title"], info["artist"],probability

#___________________________________________________________________________________
def run_demo(database, record_seconds=10):
    print("Please play the song now!")
    samples, sample_rate = load_audio("mic", mic_duration=record_seconds)

    result= identify_clip(samples, sample_rate, database)

    if result is None:
        print("No confident match found.")
    else:
        title, artist, probability = result
        print( f"We are {probability:.1f}% sure that "f"'{title}' by {artist} is playing.")
