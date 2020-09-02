import logging

from django.conf import settings
from django.contrib.auth.models import User
from social_django.models import UserSocialAuth
from spotipy import Spotify
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOAuth


spotipy_logger = logging.getLogger("spotipy.client")


def _get_spotify_social_auth(user: User) -> UserSocialAuth:
    return user.social_auth.get(provider="spotify")


def _get_spotify_extra_data(user: User) -> dict:
    return _get_spotify_social_auth(user).extra_data


def _get_spotify_access_token(user: User) -> str:
    return _get_spotify_extra_data(user)["access_token"]


def _get_spotify_refresh_token(user: User) -> str:
    return _get_spotify_extra_data(user)["refresh_token"]


def get_spotify_client(user: User, check_access: bool = True) -> Spotify:
    client = Spotify(auth=_get_spotify_access_token(user))

    if check_access:
        # Squelch logging for Spotipy, as it causes some noise for
        # caught exceptions.
        spotipy_logger.setLevel(logging.CRITICAL)

        try:
            client.currently_playing()
        except SpotifyException:
            new_auth = refresh_spotify_tokens(user)
            client = Spotify(auth=new_auth["access_token"])

            # If an exception gets raised here, then the refresh failed.
            client.currently_playing()
        finally:
            # Reenable Spotipy logging.
            spotipy_logger.setLevel(logging.NOTSET)

    return client


def refresh_spotify_tokens(user: User) -> dict:
    auth_manager = SpotifyOAuth(
        client_id=settings.SOCIAL_AUTH_SPOTIFY_KEY,
        client_secret=settings.SOCIAL_AUTH_SPOTIFY_SECRET,
        redirect_uri=settings.SPOTIFY_REDIRECT_URI,
    )
    new_auth = auth_manager.refresh_access_token(_get_spotify_refresh_token(user))
    spotify_social_auth = _get_spotify_social_auth(user)
    spotify_social_auth.extra_data = new_auth
    spotify_social_auth.save()

    return new_auth
