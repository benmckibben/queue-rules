from datetime import datetime, timezone
from typing import Iterable, Optional

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Max
from spotipy import Spotify
from spotipy.exceptions import SpotifyException

from .exceptions import BadSpotifyTrackID
from .user_utils import get_spotify_client


def _make_track_name(track_info):
    artist_names = ", ".join([x["name"] for x in track_info["artists"]])
    return f'{artist_names} - {track_info["name"]}'


class Rule(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rules")
    name = models.CharField(max_length=256, default="Unnamed")
    created = models.DateTimeField(auto_now_add=True)
    trigger_song_spotify_id = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)
    last_applied = models.DateTimeField(null=True, default=None)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("trigger_song_spotify_id", "owner"), name="unique_song_owner"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.trigger_song_spotify_id})"

    def get_song_sequence(self) -> Iterable["SongSequenceMember"]:
        return self.song_sequence.order_by("sequence_number")

    def apply(self, client: Optional[Spotify] = None) -> None:
        if client is None:
            client = get_spotify_client(self.owner)

        sequence = self.get_song_sequence()
        for song in sequence:
            client.add_to_queue(song.song_spotify_id)

        self.last_applied = datetime.now(timezone.utc)
        self.save()

    def set_name(self, client: Optional[Spotify] = None) -> None:
        if client is None:
            client = get_spotify_client(self.owner)

        try:
            track = client.track(self.trigger_song_spotify_id)
        except SpotifyException as e:
            if e.http_status in {400, 404}:
                raise BadSpotifyTrackID(self.trigger_song_spotify_id)
            else:
                raise

        self.name = _make_track_name(track)
        self.save()


class SongSequenceMember(models.Model):
    rule = models.ForeignKey(
        Rule, on_delete=models.CASCADE, related_name="song_sequence"
    )
    name = models.CharField(max_length=256, default="Unnamed")
    song_spotify_id = models.CharField(max_length=64)
    sequence_number = models.IntegerField(null=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("rule", "sequence_number"), name="unique_rule_sequence_number"
            ),
        ]
        ordering = ["sequence_number"]

    def __str__(self):
        return f"{self.name} ({self.song_spotify_id}, number {self.sequence_number})"

    def set_name(self, client: Optional[Spotify] = None) -> None:
        if client is None:
            client = get_spotify_client(self.rule.owner)

        try:
            track = client.track(self.song_spotify_id)
        except SpotifyException as e:
            if e.http_status in {400, 404}:
                raise BadSpotifyTrackID(self.song_spotify_id)
            else:
                raise

        self.name = _make_track_name(track)
        self.save()


class LastCheckLog(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="last_check_log"
    )
    last_checked = models.DateTimeField(null=False, db_index=True)

    @classmethod
    def get_most_recent_check(cls):
        return cls.objects.all().aggregate(Max("last_checked"))["last_checked__max"]


class UserLock(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="lock")
