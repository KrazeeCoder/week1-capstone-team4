import pickle
import os

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

    # Nishanth Part:
    def store_fingerprints(self, song_id, fingerprints):
        """Appends fanout tuples to self.fingerprints."""
        pass

    def query(self, clip_fingerprints):
        """Handles the offset tallying and returns best match/confidence."""
        pass
        
    def _scrub_fingerprints(self, song_id):
        """Removes a deleted song's tuples from the self.fingerprints."""
        pass






      
