import logging
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from time import sleep
from typing import ContextManager, Optional

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError
from spotipy import Spotify

from data.models import LastCheckLog, Rule, UserLock
from data.user_utils import get_spotify_client


SHORT_TRACK_CUTOFF_MS = 60000
TRACK_PROGRESS_CUTOFF = 0.5


logger = logging.getLogger("queuerd")


@contextmanager
def get_user() -> ContextManager[Optional[User]]:
    # Prioritize users with no last checked data.
    user = User.objects.filter(lock=None, last_check_log=None).first()
    if user is not None:
        # Go ahead and create a last check log while we're at it.
        LastCheckLog.objects.create(user=user, last_checked=datetime.now(timezone.utc))
    else:
        # Otherwise, find users that haven't been checked for QUEUERD_CHECK_INTERVAL
        # seconds.
        last_checked_upper_bound = datetime.now(timezone.utc) - timedelta(
            seconds=settings.QUEUERD_CHECK_INTERVAL
        )
        user = (
            User.objects.filter(
                lock=None,
                last_check_log__last_checked__lte=last_checked_upper_bound,
            )
            .order_by("last_check_log__last_checked")
            .first()
        )

    if user is None:
        yield None
    else:
        try:
            lock = UserLock.objects.create(user=user)
        except IntegrityError:  # Sometimes we'll still hit this race condition.
            logger.warn(f"Race condition when trying to lock user {user.id}")
            yield None
        else:
            try:
                yield user
            finally:
                lock.delete()


def get_matching_rule(user: User, song_id: str) -> Optional[Rule]:
    try:
        return user.rules.get(trigger_song_spotify_id=song_id, is_active=True)
    except Rule.DoesNotExist:
        return None


def should_apply_rule(rule: Rule, playback_info: dict) -> bool:
    # Deffo do not apply the rule if the track isn't playing.
    if not playback_info["is_playing"]:
        return False

    # Since we can't inspect the queue with Spotify's API, do some finnicky guesswork.

    # Firstly, has it been at least one song length since this rule was last applied?
    # This attempts to avoid the most naive case of applying a rule twice during a
    # song's single play, where the user has not paused at all.
    track_duration_ms = playback_info["item"]["duration_ms"]
    upper_bound = datetime.now(timezone.utc) - timedelta(milliseconds=track_duration_ms)
    if rule.last_applied is not None and rule.last_applied >= upper_bound:
        return False

    # Secondly, if the track is short, just say yes. Further calculations are somewhat
    # meaningless for shorter tracks.
    if track_duration_ms < SHORT_TRACK_CUTOFF_MS:
        return True

    # Thirdly, are we sufficiently through enough of the track? If we aren't yet, maybe
    # we just wait for the next run.
    progress_ms = playback_info["progress_ms"]
    if progress_ms / track_duration_ms < TRACK_PROGRESS_CUTOFF:
        return False

    # If we're at this point, we should apply the rule.
    return True


def run_for_user(user: User, client: Spotify) -> None:
    # Get the user's currently playing track.
    currently_playing = client.currently_playing()
    if currently_playing is None:
        return

    # See if there's a rule for the track.
    currently_playing_track_id = currently_playing["item"]["id"]
    rule = get_matching_rule(user, currently_playing_track_id)
    if rule is None:
        logger.debug(f"Skipping user {user.username}, no matching rule")
        return

    # See if we should apply the rule.
    should_apply = should_apply_rule(rule, currently_playing)
    if not should_apply:
        logger.debug(
            f"Not applying existing rule {rule.id} for {currently_playing_track_id}"
        )
        return

    # Apply the rule.
    logger.info(f"Applying rule {rule.id} for {currently_playing_track_id}")
    rule.apply(client)


def run_one() -> None:
    with get_user() as user:
        if user is None:
            logger.debug("No users to check now")
            return

        logger.info(f"Checking user {user.username}")

        client = get_spotify_client(user)
        run_for_user(user, client)

        last_check_log = user.last_check_log
        last_check_log.last_checked = datetime.now(timezone.utc)
        last_check_log.save()


class Command(BaseCommand):
    help = "Runs the queuer daemon, responsible for adding songs to users' queues."

    def add_arguments(self, parser):
        parser.add_argument(
            "-o",
            "--run-once",
            action="store_true",
            default=False,
            help="Check and run for one user and then exit.",
        )

    def handle(self, *args, **options):
        if options["run_once"]:
            run_one()
            return

        while True:
            run_one()
            sleep(settings.QUEUERD_SLEEP_TIME)
