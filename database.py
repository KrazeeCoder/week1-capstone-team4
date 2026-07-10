import pickle
import os
import song_metadata

class AudioDatabase:
    def __init__(self, db_filepath="data.pkl"):
        self.db_filepath = db_filepath
        
        # Apurva / Sriram: Metadata Storage
        # Format: {song_id: {"title": title, "artist": artist}}
        self.metadata = {}
        
        # Nihanth: Peak-pair encoding storage
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

    def save_data(self, filepath=None):
        target = filepath or self.db_filepath
        payload = {
            "metadata": self.metadata,
            "fingerprints": self.fingerprints,
        }
        with open(target, "wb") as file_obj:
            pickle.dump(payload, file_obj)

    def load_data(self, filepath=None):
        target = filepath or self.db_filepath
        if not os.path.exists(target):
            return

        with open(target, "rb") as file_obj:
            payload = pickle.load(file_obj)

        self.metadata = payload.get("metadata", {})
        self.fingerprints = payload.get("fingerprints", {})


    # Nihanth Part:
    def store_fingerprints(self, song_id, fingerprints):
        """Appends fanout tuples to self.fingerprints."""
        for fingerprint_hash, anchor_time in fingerprints:
            if fingerprint_hash not in self.fingerprints:
                self.fingerprints[fingerprint_hash] = []
            self.fingerprints[fingerprint_hash].append((song_id, anchor_time))

    def query(self, clip_fingerprints):
        """Handles the offset tallying and returns best match/confidence."""
        offset_tallies = {}
        for fingerprint_hash, clip_anchor_time in clip_fingerprints:
            peak_pair_matches = self.fingerprints.get(fingerprint_hash, [])

            for song_id, db_anchor_time in peak_pair_matches:
                offset = db_anchor_time - clip_anchor_time

                if song_id not in offset_tallies:
                    offset_tallies[song_id] = {}

                if offset in offset_tallies[song_id]:
                    offset_tallies[song_id][offset] += 1
                else:
                    offset_tallies[song_id][offset] = 1

        # For each song, use its best offset tally as its score
        song_scores = []
        for song_id, tallies in offset_tallies.items():
            best_score = max(tallies.values())
            song_scores.append((song_id, best_score))

        # Sort highest-scoring songs first
        song_scores.sort(key=lambda item: item[1], reverse=True)

        # Keep only the top 3 songs
        top_3 = song_scores[:3]

        if not top_3:
            return {"best_matches": {}}

        # Turn top 3 scores into probabilities
        total_score = sum(score for _, score in top_3)

        best_matches = {
            song_id: score / total_score
            for song_id, score in top_3
        }

        return {"best_matches": best_matches}

        
    def _scrub_fingerprints(self, song_id):
        """Removes a deleted song's tuples from the self.fingerprints."""
        empty_keys = []

        for fingerprint_hash, songs_list in self.fingerprints.items():
            # songs that don't match songid
            filtered_songs = [
                (stored_song_id, anchor_time)
                for stored_song_id, anchor_time in songs_list
                if stored_song_id != song_id
            ]

            if filtered_songs:
                self.fingerprints[fingerprint_hash] = filtered_songs
            else:
                empty_keys.append(fingerprint_hash)
        # if all the songs that have that peak_pair encoding is the one that is trying to be deleted.
        for fingerprint_hash in empty_keys:
            del self.fingerprints[fingerprint_hash]
