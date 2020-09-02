import logging
from datetime import datetime, timedelta, timezone
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db.utils import IntegrityError
from django.test import TestCase
from freezegun import freeze_time

from data.models import LastCheckLog, Rule, UserLock
from worker.management.commands import queuerd


class TestGetUser(TestCase):
    def setUp(self):
        # Squelch logging for these tests.
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        # Reenable logging when tests finish.
        logging.disable(logging.NOTSET)

    def test_no_users(self):
        with queuerd.get_user() as user:
            self.assertIsNone(user)

    def test_basic_one_user_with_log(self):
        test_user = User.objects.create(username="test")

        LastCheckLog.objects.create(
            user=test_user,
            last_checked=datetime(1985, 2, 15, tzinfo=timezone.utc),
        )

        with queuerd.get_user() as user:
            self.assertEqual(
                user,
                test_user,
            )
            # Test that a lock was created.
            self.assertTrue(UserLock.objects.filter(user=test_user).exists())

        # Also check that the lock was released.
        self.assertFalse(UserLock.objects.filter(user=test_user).exists())

    def test_only_locked_users(self):
        test_user = User.objects.create(username="test")
        UserLock.objects.create(user=test_user)

        with queuerd.get_user() as user:
            self.assertIsNone(user)

    def test_prioritize_never_checked_user(self):
        test_user_1 = User.objects.create(username="test1")
        test_user_2 = User.objects.create(username="test2")

        LastCheckLog.objects.create(
            user=test_user_2, last_checked=datetime(2000, 5, 7, tzinfo=timezone.utc)
        )

        with queuerd.get_user() as user:
            self.assertEqual(
                user,
                test_user_1,
            )
            # Test that a lock was created.
            self.assertTrue(UserLock.objects.filter(user=test_user_1).exists())

        # Also check that a new log was created for the unchecked user.
        self.assertTrue(LastCheckLog.objects.filter(user=test_user_1).exists())

        # Also check that the lock was released.
        self.assertFalse(UserLock.objects.filter(user=test_user_1).exists())

    def test_prioritize_less_recently_checked_user(self):
        test_user_1 = User.objects.create(username="test1")
        test_user_2 = User.objects.create(username="test2")

        LastCheckLog.objects.create(
            user=test_user_1, last_checked=datetime(2000, 5, 7, tzinfo=timezone.utc)
        )
        LastCheckLog.objects.create(
            user=test_user_2, last_checked=datetime(1985, 5, 7, tzinfo=timezone.utc)
        )

        with queuerd.get_user() as user:
            self.assertEqual(
                user,
                test_user_2,
            )
            # Test that a lock was created.
            self.assertTrue(UserLock.objects.filter(user=test_user_2).exists())

        # Also check that the lock was released.
        self.assertFalse(UserLock.objects.filter(user=test_user_2).exists())

    @freeze_time("2020-02-15")
    def test_one_user_too_recently_checked(self):
        test_user = User.objects.create(username="test")

        LastCheckLog.objects.create(
            user=test_user,
            last_checked=datetime(2020, 2, 15, tzinfo=timezone.utc)
            - timedelta(
                seconds=settings.QUEUERD_CHECK_INTERVAL - 1,
            ),
        )

        with queuerd.get_user() as user:
            self.assertIsNone(user)

    @mock.patch("worker.management.commands.queuerd.UserLock")
    def test_race_condition(self, mock_UserLock):
        User.objects.create(username="test")
        mock_UserLock.objects.create.side_effect = IntegrityError()

        with queuerd.get_user() as user:
            self.assertIsNone(user)


class TestGetMatchingRule(TestCase):
    def setUp(self):
        self.test_user = User.objects.create(username="test")
        self.test_rule = Rule.objects.create(
            owner=self.test_user, trigger_song_spotify_id="foo"
        )

    def test_rule_matched(self):
        self.assertEqual(
            queuerd.get_matching_rule(self.test_user, "foo"),
            self.test_rule,
        )

    def test_no_rule_matched(self):
        self.assertIsNone(queuerd.get_matching_rule(self.test_user, "bar"))

    def test_inactive_rule(self):
        self.test_rule.is_active = False
        self.test_rule.save()

        self.assertIsNone(
            queuerd.get_matching_rule(self.test_user, "foo"),
            self.test_rule,
        )


class TestShouldApplyRule(TestCase):
    def setUp(self):
        self.test_user = User.objects.create(username="test")
        self.test_rule = Rule.objects.create(
            owner=self.test_user, trigger_song_spotify_id="foo"
        )

    def test_not_playing(self):
        self.assertFalse(
            queuerd.should_apply_rule(
                self.test_rule,
                {"is_playing": False},
            )
        )

    def test_inactive(self):
        self.test_rule.is_active = False
        self.test_rule.save()

        self.assertFalse(
            queuerd.should_apply_rule(
                self.test_rule,
                {"is_playing": True},
            )
        )

    @freeze_time("2020-05-17")
    def test_too_soon_to_apply(self):
        playback_info = {"is_playing": True, "item": {"duration_ms": 180000}}

        too_soon_rule = Rule.objects.create(
            owner=self.test_user,
            trigger_song_spotify_id="bar",
            last_applied=datetime(2020, 5, 17, tzinfo=timezone.utc)
            - timedelta(minutes=2),
        )

        self.assertFalse(queuerd.should_apply_rule(too_soon_rule, playback_info))

    def test_too_short_to_care(self):
        playback_info = {
            "is_playing": True,
            "item": {"duration_ms": queuerd.SHORT_TRACK_CUTOFF_MS - 1},
        }

        self.assertTrue(queuerd.should_apply_rule(self.test_rule, playback_info))

    def test_not_far_enough_in_song(self):
        playback_info = {
            "is_playing": True,
            "progress_ms": (900000 * queuerd.TRACK_PROGRESS_CUTOFF) - 1,
            "item": {"duration_ms": 900000},
        }

        self.assertFalse(queuerd.should_apply_rule(self.test_rule, playback_info))

    def test_all_checks_passed(self):
        playback_info = {
            "is_playing": True,
            "progress_ms": (900000 * queuerd.TRACK_PROGRESS_CUTOFF) + 1,
            "item": {"duration_ms": 900000},
        }

        self.assertTrue(queuerd.should_apply_rule(self.test_rule, playback_info))


class TestRunForUser(TestCase):
    def setUp(self):
        # Squelch logging for these tests.
        logging.disable(logging.CRITICAL)

        self.test_user = User.objects.create(username="test")
        self.test_rule = Rule.objects.create(
            owner=self.test_user, trigger_song_spotify_id="foo"
        )
        self.test_rule.apply = mock.MagicMock()

    def tearDown(self):
        # Reenable logging when tests finish.
        logging.disable(logging.NOTSET)

    def test_not_playing(self):
        mock_client = mock.MagicMock()
        mock_client.currently_playing.return_value = None

        queuerd.run_for_user(self.test_user, mock_client)

        self.test_rule.apply.assert_not_called()

    def test_none_item(self):
        mock_client = mock.MagicMock()
        mock_client.currently_playing.return_value = {"item": None}

        queuerd.run_for_user(self.test_user, mock_client)

        self.test_rule.apply.assert_not_called()

    @mock.patch("worker.management.commands.queuerd.get_matching_rule")
    def test_no_matching_rule(self, mock_get_matching):
        mock_client = mock.MagicMock()
        mock_client.currently_playing.return_value = {
            "item": {"id": "bar"},
        }
        mock_get_matching.return_value = None

        queuerd.run_for_user(self.test_user, mock_client)

        mock_get_matching.assert_called_once_with(self.test_user, "bar")
        self.test_rule.apply.assert_not_called()

    @mock.patch("worker.management.commands.queuerd.get_matching_rule")
    @mock.patch("worker.management.commands.queuerd.should_apply_rule")
    def test_shouldnt_apply_matching_rule(self, mock_should_apply, mock_get_matching):
        mock_client = mock.MagicMock()
        mock_client.currently_playing.return_value = {
            "item": {"id": "foo"},
        }
        mock_get_matching.return_value = self.test_rule
        mock_should_apply.return_value = False

        queuerd.run_for_user(self.test_user, mock_client)

        mock_get_matching.assert_called_once_with(self.test_user, "foo")
        mock_should_apply.assert_called_once_with(
            self.test_rule, mock_client.currently_playing.return_value
        )
        self.test_rule.apply.assert_not_called()

    @mock.patch("worker.management.commands.queuerd.get_matching_rule")
    @mock.patch("worker.management.commands.queuerd.should_apply_rule")
    def test_should_apply_matching_rule(self, mock_should_apply, mock_get_matching):
        mock_client = mock.MagicMock()
        mock_client.currently_playing.return_value = {
            "item": {"id": "foo"},
        }
        mock_get_matching.return_value = self.test_rule
        mock_should_apply.return_value = True

        queuerd.run_for_user(self.test_user, mock_client)

        mock_get_matching.assert_called_once_with(self.test_user, "foo")
        mock_should_apply.assert_called_once_with(
            self.test_rule, mock_client.currently_playing.return_value
        )
        self.test_rule.apply.assert_called_once_with(mock_client)


class TestRunOne(TestCase):
    def setUp(self):
        # Squelch logging for these tests.
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        # Reenable logging when tests finish.
        logging.disable(logging.NOTSET)

    @mock.patch("worker.management.commands.queuerd.get_spotify_client")
    @mock.patch("worker.management.commands.queuerd.get_user")
    def test_no_user(self, mock_get_user, mock_get_spotify_client):
        mock_get_user.return_value.__enter__.return_value = None
        mock_get_user.return_value.__exit__.return_value = None

        queuerd.run_one()

        # Ensure we didn't get to this point in the function.
        mock_get_spotify_client.assert_not_called()

    @freeze_time("2020-08-16")
    @mock.patch("worker.management.commands.queuerd.run_for_user")
    @mock.patch("worker.management.commands.queuerd.get_spotify_client")
    @mock.patch("worker.management.commands.queuerd.get_user")
    def test_with_user(self, mock_get_user, mock_get_spotify_client, mock_run_for_user):
        test_user = User.objects.create(username="test")
        test_user_log = LastCheckLog.objects.create(
            user=test_user, last_checked=datetime(1985, 12, 25, tzinfo=timezone.utc)
        )

        mock_get_user.return_value.__enter__.return_value = test_user
        mock_get_user.return_value.__exit__.return_value = None
        mock_spotify_client = mock.MagicMock()
        mock_get_spotify_client.return_value = mock_spotify_client

        queuerd.run_one()

        mock_get_spotify_client.assert_called_once_with(test_user)
        mock_run_for_user.assert_called_once_with(test_user, mock_spotify_client)

        test_user_log.refresh_from_db()
        self.assertEqual(
            test_user_log.last_checked,
            datetime(2020, 8, 16, tzinfo=timezone.utc),
        )


class TestCommand(TestCase):
    class TestCommandIntentionalException(Exception):
        pass

    @mock.patch("worker.management.commands.queuerd.run_one")
    @mock.patch("worker.management.commands.queuerd.sleep")
    def test_run_once(self, mock_sleep, mock_run_one):
        call_command("queuerd", "-o")

        mock_run_one.assert_called_once()
        mock_sleep.assert_not_called()

    @mock.patch("worker.management.commands.queuerd.run_one")
    @mock.patch("worker.management.commands.queuerd.sleep")
    def test_run_forever(self, mock_sleep, mock_run_one):
        mock_sleep.side_effect = [True, TestCommand.TestCommandIntentionalException()]

        with self.assertRaises(TestCommand.TestCommandIntentionalException):
            call_command("queuerd")

        self.assertEqual(len(mock_run_one.mock_calls), 2)
        mock_sleep.assert_called_with(settings.QUEUERD_SLEEP_TIME)
