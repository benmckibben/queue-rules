from datetime import datetime, timezone
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from freezegun import freeze_time

from data.management.commands.clear_user_locks import _parse_datetime
from data.models import UserLock


class TestParseDatetime(SimpleTestCase):
    def test_bad_input(self):
        with self.assertRaises(ValueError):
            _parse_datetime("blah")

    def test_12_hour_time(self):
        dt = _parse_datetime("2020-09-04T05:12:25")

        self.assertEqual(
            dt,
            datetime(2020, 9, 4, 5, 12, 25, tzinfo=timezone.utc),
        )

    def test_24_hour_time(self):
        dt = _parse_datetime("2020-09-08T18:13:54")

        self.assertEqual(
            dt,
            datetime(2020, 9, 8, 18, 13, 54, tzinfo=timezone.utc),
        )


class TestCommand(TestCase):
    def test_no_locks_exist(self):
        self.assertFalse(UserLock.objects.exists())

        call_command("clear_user_locks", stdout=StringIO())

        self.assertFalse(UserLock.objects.exists())

    def test_delete_all_locks(self):
        UserLock.objects.create(user=User.objects.create(username="test1"))
        UserLock.objects.create(user=User.objects.create(username="test2"))
        self.assertEqual(UserLock.objects.count(), 2)

        call_command("clear_user_locks", stdout=StringIO())

        self.assertFalse(UserLock.objects.exists())

    def test_delete_created_before(self):
        with freeze_time("2020-08-30 23:59:59"):
            UserLock.objects.create(user=User.objects.create(username="test1"))

        with freeze_time("2020-08-31 00:00:00"):
            test_lock_2 = UserLock.objects.create(
                user=User.objects.create(username="test2")
            )

        self.assertEqual(UserLock.objects.count(), 2)

        call_command(
            "clear_user_locks",
            created_before="2020-08-31T00:00:00",
            stdout=StringIO(),
        )

        self.assertEqual(UserLock.objects.count(), 1)
        self.assertEqual(
            UserLock.objects.get(),
            test_lock_2,
        )
