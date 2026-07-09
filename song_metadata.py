#gives songs a unique ID, song_metadata is a dict
def get_song_id(song_metadata):
    if len(song_metadata) == 0:
        return 0
    return max(song_metadata.keys()) + 1
