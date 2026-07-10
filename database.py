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
        pass

    def query(self, clip_fingerprints):
        """Handles the offset tallying and returns best match/confidence."""
        pass
        
    def _scrub_fingerprints(self, song_id):
        """Removes a deleted song's tuples from the self.fingerprints."""
        pass
