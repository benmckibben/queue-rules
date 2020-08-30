from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from social_django.models import UserSocialAuth
from spotipy.exceptions import SpotifyException

from data import user_utils


class TestUserUtils(TestCase):
    def setUp(self):
        self.test_user = User.objects.create(username="test")
        self.test_social_auth_extra_data = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
        }
        self.test_social_auth = UserSocialAuth.objects.create(
            user=self.test_user,
            provider="spotify",
            uid="test",
            extra_data=self.test_social_auth_extra_data,
        )

    def test_get_spotify_social_auth(self):
        self.assertEqual(
            user_utils._get_spotify_social_auth(self.test_user),
            self.test_social_auth,
        )

    def test_get_spotify_extra_data(self):
        self.assertEqual(
            user_utils._get_spotify_extra_data(self.test_user),
            self.test_social_auth_extra_data,
        )

    def test_get_spotify_access_token(self):
        self.assertEqual(
            user_utils._get_spotify_access_token(self.test_user),
            "test_access_token",
        )

    @mock.patch("data.user_utils.Spotify")
    def test_get_spotify_client_no_check(self, mock_spotify_class):
        _ = user_utils.get_spotify_client(self.test_user, False)
        mock_spotify_class.assert_called_once_with(
            auth=self.test_social_auth_extra_data["access_token"]
        )

    @mock.patch("data.user_utils.Spotify")
    def test_get_spotify_client_check_no_refresh(self, mock_spotify_class):
        mock_spotify_client = mock.MagicMock()
        mock_spotify_client.currently_playing.return_value = True
        mock_spotify_class.return_value = mock_spotify_client

        _ = user_utils.get_spotify_client(self.test_user, True)
        mock_spotify_client.currently_playing.assert_called_once()

    @mock.patch("data.user_utils.refresh_spotify_tokens")
    @mock.patch("data.user_utils.Spotify")
    def test_get_spotify_client_check_refresh_sucess(
        self,
        mock_spotify_class,
        mock_refresh_function,
    ):
        mock_spotify_client = mock.MagicMock()
        mock_spotify_client.currently_playing.side_effect = [
            SpotifyException(403, 403, "whoopsie"),
            True,
        ]
        mock_spotify_class.return_value = mock_spotify_client

        mock_refresh_function.return_value = {"access_token": "refreshed_auth"}

        _ = user_utils.get_spotify_client(self.test_user, True)

        self.assertEqual(len(mock_spotify_client.currently_playing.mock_calls), 2)
        mock_refresh_function.assert_called_once_with(self.test_user)
        self.assertEqual(
            mock_spotify_class.mock_calls,
            [
                mock.call(auth=self.test_social_auth_extra_data["access_token"]),
                mock.call().currently_playing(),
                mock.call(auth="refreshed_auth"),
                mock.call().currently_playing(),
            ],
        )

    @mock.patch("data.user_utils.refresh_spotify_tokens")
    @mock.patch("data.user_utils.Spotify")
    def test_get_spotify_client_check_refresh_fail(
        self,
        mock_spotify_class,
        mock_refresh_function,
    ):
        mock_spotify_client = mock.MagicMock()
        mock_spotify_client.currently_playing.side_effect = SpotifyException(
            403,
            403,
            "whoopsie",
        )
        mock_spotify_class.return_value = mock_spotify_client

        mock_refresh_function.return_value = {"access_token": "refreshed_auth"}

        with self.assertRaises(SpotifyException):
            _ = user_utils.get_spotify_client(self.test_user, True)

        self.assertEqual(len(mock_spotify_client.currently_playing.mock_calls), 2)
        mock_refresh_function.assert_called_once_with(self.test_user)
        self.assertEqual(
            mock_spotify_class.mock_calls,
            [
                mock.call(auth=self.test_social_auth_extra_data["access_token"]),
                mock.call().currently_playing(),
                mock.call(auth="refreshed_auth"),
                mock.call().currently_playing(),
            ],
        )

    @mock.patch("data.user_utils.SpotifyOAuth")
    def test_refresh_spotify_tokens(self, mock_oauth_class):
        mock_oauth_instance = mock.MagicMock()
        mock_oauth_instance.refresh_access_token.return_value = {
            "access_token": "refreshed_access_token",
            "refresh_token": "refreshed_refresh_token",
        }
        mock_oauth_class.return_value = mock_oauth_instance

        new_auth = user_utils.refresh_spotify_tokens(self.test_user)

        self.assertEqual(new_auth["access_token"], "refreshed_access_token")
        self.assertEqual(new_auth["refresh_token"], "refreshed_refresh_token")
        mock_oauth_class.assert_called_once()
        mock_oauth_instance.refresh_access_token.assert_called_once_with(
            "test_refresh_token"
        )
        self.assertEqual(
            self.test_user.social_auth.get(provider="spotify").extra_data[
                "access_token"
            ],
            "refreshed_access_token",
        )
        self.assertEqual(
            self.test_user.social_auth.get(provider="spotify").extra_data[
                "refresh_token"
            ],
            "refreshed_refresh_token",
        )
