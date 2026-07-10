import pickle
import os

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
    def save_data(self, filepath=None):
        pass

    def load_data(self, filepath=None):
        pass

    def add_song(self, title, artist):
        """Stops duplicates, returns new song_id."""
        pass

    def inspect_database(self):
        """Prints all songs in the database."""
        pass

    def delete_song(self, song_id):
        """Deletes metadata and does the fingerprint cleanup."""
        pass

    # Nihanth Part:
    def store_fingerprints(self, song_id, fingerprints):
      """Appends fanout tuples to self.fingerprints."""
    for fingerprint_hash, anchor_time in fingerprints:
        if fingerprint_hash in self.fingerprints:
            self.fingerprints[fingerprint_hash].append((song_id, anchor_time))
        else:
            self.fingerprints[fingerprint_hash] = [(song_id, anchor_time)]


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

    def delete_song(self, song_id):
        self._scrub_fingerprints(song_id)
        self.metadata.pop(song_id, None)    

