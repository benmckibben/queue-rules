class BadSpotifyTrackID(Exception):
    def __init__(self, track_id):
        self.track_id = track_id
        self.message = f"Bad Spotify track ID: {track_id}"
        super().__init__(self.message)
