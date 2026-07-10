import pickle
import os
import song_metadata

class AudioDatabase:
    def __init__(self, db_filepath="data.pkl"):
        self.db_filepath = db_filepath
        
        # Apurva / Sriram: Metadata Storage
        # Format: {song_id: {"title": title, "artist": artist}}
        self.metadata = {}
        
        # Nihanth: Fingerprint Storage
        # Format: {(f1, f2, dt): [(song_id, anchor_time), ...]}
        self.fingerprints = {} 

    # Sriam Part:
    def inspect_database(self):
        if not self.metadata:
            print("The database is emptyy")
            return
            
        print(f"\n{'ID':<5} | {'Title':<30} | {'Artist':<20} | {'Filename'}")
        print("-" * 80)
        
        songs = song_metadata.list_songs(self.metadata)
        for song in songs:
            print(f"{song['song_id']:<5} | {song['title']:<30} | {song['artist']:<20} | {song['filename']}")
        print("\n")

    def add_song(self, title, artist, filename):
        
        new_id = song_metadata.add_song_metadata(self.metadata, title, artist, filename)
        print(f"Processed, '{title}' by {artist}. DB ID is: {new_id}")
        return new_id

    def delete_song(self, song_id):
        if song_id in self.metadata:
            info = self.metadata.pop(song_id)
            print(f"Deleted '{info['title']}' from the metadata.")
            self._scrub_fingerprints(song_id)
        else:
            print(f"Song ID {song_id} not found.")

    # Nishanth Part:
    def store_fingerprints(self, song_id, fingerprints):
        """Appends fanout tuples to self.fingerprints."""
        for fingerprint_hash, anchor_time in fingerprints:
            self.fingerprints.setdefault(fingerprint_hash, []).append((song_id, anchor_time))

    def save_data(self, filepath=None):
        target = filepath or self.db_filepath
        payload = {
            "metadata": self.metadata,
            "fingerprints": self.fingerprints,
        }
        with open(target, "wb") as f:
            pickle.dump(payload, f)

    def load_data(self, filepath=None):
        target = filepath or self.db_filepath
        if not os.path.exists(target):
            return
        with open(target, "rb") as f:
            payload = pickle.load(f)
        self.metadata = payload.get("metadata", {})
        self.fingerprints = payload.get("fingerprints", {})

    def query(self, clip_fingerprints):
        """Handles the offset tallying and returns best match/confidence."""
        pass
        
    def _scrub_fingerprints(self, song_id):
        """Removes a deleted song's tuples from the self.fingerprints."""
        keys_to_delete = []
        for fp_hash, matches in self.fingerprints.items():
            filtered = [entry for entry in matches if entry[0] != song_id]
            if filtered:
                self.fingerprints[fp_hash] = filtered
            else:
                keys_to_delete.append(fp_hash)

        for fp_hash in keys_to_delete:
            del self.fingerprints[fp_hash]
