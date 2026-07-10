from load_audio import load_audio
from create_spectogram import create_spectrogram
from find_peaks import find_peaks
from create_fingerprints import peaks_to_fingerprints
from database import AudioDatabase
from final_checker import run_demo


def add_song(db):
	wav_path = input("Enter the path to the WAV file: ").strip()
	title = input("Enter song title: ").strip()
	artist = input("Enter artist name: ").strip()

	samples, rate = load_audio(wav_path)
	spectrogram, _, _ = create_spectrogram(samples, rate)
	peaks = find_peaks(spectrogram)
	fingerprints = peaks_to_fingerprints(peaks)

	song_id = db.add_song(title, artist, wav_path)
	db.store_fingerprints(song_id, fingerprints)
	db.save_data()
	
	print(f"Stored {len(fingerprints)} fingerprints for song ID {song_id}.")
	print(f"Added '{title}' by {artist} to the database.")

def main():
	db = AudioDatabase("data.pkl")
	db.load_data()

	choice = input("Add a song (1) or identify what's playing (2)? ").strip().lower()

	if choice == "1":
		add_song(db)
	elif choice == "2":
		run_demo(db)
	else:
		print("Unrecognized option, please enter '1' or '2'.")


if __name__ == "__main__":
	main()
