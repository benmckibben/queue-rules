from datetime import datetime, timezone
from unittest import mock

from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.test import SimpleTestCase, TestCase
from freezegun import freeze_time
from spotipy.exceptions import SpotifyException

from data.exceptions import BadSpotifyTrackID
from data.models import (
    Rule,
    LastCheckLog,
    SongSequenceMember,
    UserLock,
    _make_track_name,
)


class TestMakeTrackName(SimpleTestCase):
    def test_single_artist(self):
        track_info = {
            "artists": [{"name": "Lil B"}],
            "name": "I Own Swag",
        }
        self.assertEqual(
            _make_track_name(track_info),
            "Lil B - I Own Swag",
        )

    def test_multiple_artists(self):
        track_info = {
            "artists": [{"name": "Gwen Stefani"}, {"name": "Akon"}],
            "name": "The Sweet Escape",
        }
        self.assertEqual(
            _make_track_name(track_info),
            "Gwen Stefani, Akon - The Sweet Escape",
        )


class TestRule(TestCase):
    def setUp(self):
        self.TEST_SONG = "6sGiI7V9kgLNEhPIxEJDii"
        self.TEST_SONG_SEQ_1 = "0PtIxTsvg7N78Db2P1mC0g"
        self.TEST_SONG_SEQ_2 = "08iqsx5sRyySe5bOAm7XOV"

        self.test_user_1 = User.objects.create(username="test1")
        self.test_user_2 = User.objects.create(username="test2")
        self.test_rule = Rule.objects.create(
            owner=self.test_user_1,
            name="Grant Macdonald - Ram Ranch",
            trigger_song_spotify_id=self.TEST_SONG,
            is_active=True,
            last_applied=None,
        )

        self.test_song_seq_1 = SongSequenceMember.objects.create(
            rule=self.test_rule,
            song_spotify_id=self.TEST_SONG_SEQ_1,
            sequence_number=1,
        )
        self.test_song_seq_2 = SongSequenceMember.objects.create(
            rule=self.test_rule,
            song_spotify_id=self.TEST_SONG_SEQ_2,
            sequence_number=0,
        )

    def test_str(self):
        self.assertEqual(
            str(self.test_rule), "Grant Macdonald - Ram Ranch (6sGiI7V9kgLNEhPIxEJDii)"
        )

    def test_unqiue_song_owner(self):
        with self.assertRaises(IntegrityError):
            Rule.objects.create(
                owner=self.test_user_1,
                trigger_song_spotify_id=self.TEST_SONG,
            )

    def test_same_song_different_owner(self):
        Rule.objects.create(
            owner=self.test_user_2,
            trigger_song_spotify_id=self.TEST_SONG,
        )

    def test_get_song_sequence(self):
        self.assertEqual(
            tuple(self.test_rule.get_song_sequence()),
            (self.test_song_seq_2, self.test_song_seq_1),
        )

    @freeze_time("2026-08-16")
    @mock.patch("data.models.get_spotify_client")
    def test_apply_no_client(self, mock_get_client):
        mock_client = mock.MagicMock()
        mock_get_client.return_value = mock_client

        self.test_rule.apply()

        mock_get_client.assert_called_once()
        self.assertEqual(
            mock_client.mock_calls,
            [
                mock.call.add_to_queue(self.TEST_SONG_SEQ_2),
                mock.call.add_to_queue(self.TEST_SONG_SEQ_1),
            ],
        )

        self.assertEqual(
            self.test_rule.last_applied,
            datetime(2026, 8, 16, tzinfo=timezone.utc),
        )

    @freeze_time("2029-08-16")
    def test_apply_with_client(self):
        mock_client = mock.MagicMock()

        self.test_rule.apply(mock_client)

        self.assertEqual(
            mock_client.mock_calls,
            [
                mock.call.add_to_queue(self.TEST_SONG_SEQ_2),
                mock.call.add_to_queue(self.TEST_SONG_SEQ_1),
            ],
        )

        self.assertEqual(
            self.test_rule.last_applied,
            datetime(2029, 8, 16, tzinfo=timezone.utc),
        )

    @mock.patch("data.models._make_track_name")
    @mock.patch("data.models.get_spotify_client")
    def test_set_name_no_client(self, mock_get_client, mock_make_track_name):
        track_name = "Grant Macdonald - Ram Ranch"
        mock_make_track_name.return_value = track_name

        self.test_rule.set_name()

        mock_get_client.assert_called_once_with(self.test_user_1)
        mock_make_track_name.assert_called_once()
        self.assertEqual(self.test_rule.name, track_name)

    @mock.patch("data.models._make_track_name")
    def test_set_name_with_client(self, mock_make_track_name):
        mock_client = mock.MagicMock()

        track_name = "Grant Macdonald - Ram Ranch"
        mock_make_track_name.return_value = track_name

        self.test_rule.set_name(mock_client)

        mock_client.track.assert_called_once_with(
            self.test_rule.trigger_song_spotify_id
        )
        mock_make_track_name.assert_called_once()
        self.assertEqual(self.test_rule.name, track_name)

    def test_set_name_bad_track_id_400(self):
        mock_client = mock.MagicMock()
        mock_client.track.side_effect = SpotifyException(
            http_status=400, code=400, msg="whoops"
        )

        with self.assertRaisesMessage(BadSpotifyTrackID, f"{self.TEST_SONG}"):
            self.test_rule.set_name(mock_client)

    def test_set_name_bad_track_id_404(self):
        mock_client = mock.MagicMock()
        mock_client.track.side_effect = SpotifyException(
            http_status=404, code=404, msg="whoops"
        )

        with self.assertRaisesMessage(BadSpotifyTrackID, f"{self.TEST_SONG}"):
            self.test_rule.set_name(mock_client)

    def test_set_name_other_spotifyexception(self):
        mock_client = mock.MagicMock()
        mock_client.track.side_effect = SpotifyException(
            http_status=401, code=401, msg="whoops"
        )

        with self.assertRaises(SpotifyException):
            self.test_rule.set_name(mock_client)


class TestSongSequenceMember(TestCase):
    def setUp(self):
        self.TEST_SONG = "6sGiI7V9kgLNEhPIxEJDii"
        self.TEST_SONG_SEQ = "0PtIxTsvg7N78Db2P1mC0g"

        self.test_user = User.objects.create(username="test1")
        self.test_rule = Rule.objects.create(
            owner=self.test_user,
            trigger_song_spotify_id=self.TEST_SONG,
            is_active=True,
            last_applied=None,
        )
        self.test_song_seq = SongSequenceMember.objects.create(
            rule=self.test_rule,
            name="Grant Macdonald - Ram Ranch 3",
            song_spotify_id=self.TEST_SONG_SEQ,
            sequence_number=0,
        )

    def test_str(self):
        self.assertEqual(
            str(self.test_song_seq),
            "Grant Macdonald - Ram Ranch 3 (0PtIxTsvg7N78Db2P1mC0g, number 0)",
        )

    def test_duplicate_sequence_number(self):
        with self.assertRaises(IntegrityError):
            SongSequenceMember.objects.create(
                rule=self.test_rule,
                song_spotify_id="blah",
                sequence_number=0,
            )

    def test_same_song_different_sequence_number(self):
        SongSequenceMember.objects.create(
            rule=self.test_rule,
            song_spotify_id=self.TEST_SONG_SEQ,
            sequence_number=1,
        )

    @mock.patch("data.models._make_track_name")
    @mock.patch("data.models.get_spotify_client")
    def test_set_name_no_client(self, mock_get_client, mock_make_track_name):
        track_name = "Grant Macdonald - Ram Ranch"
        mock_make_track_name.return_value = track_name

        self.test_song_seq.set_name()

        mock_get_client.assert_called_once_with(self.test_user)
        mock_make_track_name.assert_called_once()
        self.assertEqual(self.test_song_seq.name, track_name)

    @mock.patch("data.models._make_track_name")
    def test_set_name_with_client(self, mock_make_track_name):
        mock_client = mock.MagicMock()

        track_name = "Grant Macdonald - Ram Ranch"
        mock_make_track_name.return_value = track_name

        self.test_song_seq.set_name(mock_client)

        mock_client.track.assert_called_once_with(self.test_song_seq.song_spotify_id)
        mock_make_track_name.assert_called_once()
        self.assertEqual(self.test_song_seq.name, track_name)

    def test_set_name_bad_track_id_400(self):
        mock_client = mock.MagicMock()
        mock_client.track.side_effect = SpotifyException(
            http_status=400, code=400, msg="whoops"
        )

        with self.assertRaisesMessage(BadSpotifyTrackID, f"{self.TEST_SONG_SEQ}"):
            self.test_song_seq.set_name(mock_client)

    def test_set_name_bad_track_id_404(self):
        mock_client = mock.MagicMock()
        mock_client.track.side_effect = SpotifyException(
            http_status=404, code=404, msg="whoops"
        )

        with self.assertRaisesMessage(BadSpotifyTrackID, f"{self.TEST_SONG_SEQ}"):
            self.test_song_seq.set_name(mock_client)

    def test_set_name_other_spotifyexception(self):
        mock_client = mock.MagicMock()
        mock_client.track.side_effect = SpotifyException(
            http_status=401, code=401, msg="whoops"
        )

        with self.assertRaises(SpotifyException):
            self.test_song_seq.set_name(mock_client)


class TestLastCheckLog(TestCase):
    def setUp(self):
        self.test_user_1 = User.objects.create(username="test1")
        self.test_log_1 = LastCheckLog.objects.create(
            user=self.test_user_1,
            last_checked=datetime(1985, 6, 8, tzinfo=timezone.utc),
        )

        self.test_user_2 = User.objects.create(username="test2")
        self.test_log_2 = LastCheckLog.objects.create(
            user=self.test_user_2,
            last_checked=datetime(1985, 1, 1, tzinfo=timezone.utc),
        )

    def test_two_logs_for_user(self):
        with self.assertRaises(IntegrityError):
            LastCheckLog.objects.create(
                user=self.test_user_1,
                last_checked=datetime(2020, 6, 8, tzinfo=timezone.utc),
            )

    def test_get_most_recent_check(self):
        self.assertEqual(
            LastCheckLog.get_most_recent_check(),
            datetime(1985, 6, 8, tzinfo=timezone.utc),
        )


class TestUserLock(TestCase):
    def setUp(self):
        self.test_user = User.objects.create(username="test1")
        self.test_lock = UserLock.objects.create(user=self.test_user)

    def test_two_locks_for_user(self):
        with self.assertRaises(IntegrityError):
            UserLock.objects.create(user=self.test_user)
