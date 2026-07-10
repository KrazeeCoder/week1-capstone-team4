#gives songs a unique ID, song_metadata is a dict
def get_song_id(song_metadata):
    if len(song_metadata) == 0:
        return 0
    return max(song_metadata.keys()) + 1

#adds a new song to the metadata dict
def add_song_metadata(song_metadata, title, artist, filename):
    existing_song_id = find_existing_song(song_metadata, title, artist, filename)
    if existing_song_id is not None:
        return existing_song_id
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

#shows all the songs stored in the metadata dict
def list_songs(song_metadata):
    songs = []
    for song_id, info in song_metadata.items():
        songs.append({
            "song_id": song_id,
            "title": info["title"],
            "artist": info["artist"],
            "filename": info["filename"]
        })
    return songs

#find same song in case duplicates
def find_existing_song(song_metadata, title, artist, filename):
    for song_id, info in song_metadata.items():
        if (
            info["title"] == title
            and info["artist"] == artist
            and info["filename"] == filename
        ):
            return song_id

    return None