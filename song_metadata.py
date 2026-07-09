#gives songs a unique ID, song_metadata is a dict
def get_song_id(song_metadata):
    if len(song_metadata) == 0:
        return 0
    return max(song_metadata.keys()) + 1

#adds a new song to the metadata dict
def add_song_metadata(song_metadata, title, artist, filename):
    song_id = get_song_id(song_metadata)
    song_metadata[song_id] = {
        "title": title,
        "artist": artist,
        "filename": filename
    }
    return song_id

#returns list of all songs in metadata dict
def get_song_metadata(song_metadata, song_id):
    return song_metadata[song_id]
