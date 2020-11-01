from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from freezegun import freeze_time

from api import service_checks
from data.models import LastCheckLog


class TestMostRecentCheck(TestCase):
    def setUp(self):
        self.test_user = User.objects.create(username="test1")

    @freeze_time("2020-08-15")
    def test_pass(self):
        LastCheckLog.objects.create(
            user=self.test_user,
            last_checked=datetime(2020, 8, 15, tzinfo=timezone.utc)
            - timedelta(seconds=settings.SERVICE_STATUS_OK_THRESHOLD),
        )

        check_pass, check_info = service_checks.most_recent_check()
        self.assertTrue(check_pass)
        self.assertEqual(
            {
                "most_recent_check_age": timedelta(
                    seconds=settings.SERVICE_STATUS_OK_THRESHOLD
                )
            },
            check_info,
        )

    @freeze_time("2020-08-15")
    def test_fail(self):
        LastCheckLog.objects.create(
            user=self.test_user,
            last_checked=datetime(2020, 8, 15, tzinfo=timezone.utc)
            - timedelta(seconds=settings.SERVICE_STATUS_OK_THRESHOLD)
            - timedelta(milliseconds=1),
        )

        check_pass, check_info = service_checks.most_recent_check()
        self.assertFalse(check_pass)
        self.assertEqual(
            {
                "most_recent_check_age": timedelta(
                    milliseconds=settings.SERVICE_STATUS_OK_THRESHOLD * 1000 + 1,
                )
            },
            check_info,
        )

    def test_no_check_logs(self):
        self.assertEqual(LastCheckLog.objects.count(), 0)

        check_pass, check_info = service_checks.most_recent_check()
        self.assertFalse(check_pass)
        self.assertEqual(
            {
                "most_recent_check_age": None,
            },
            check_info,
        )


class TestRunChecks(SimpleTestCase):
    def test_no_checks(self):
        service_checks.CRITICAL_CHECKS = ()
        service_checks.WARNING_CHECKS = ()

        service_status, check_info = service_checks.run_checks()

        self.assertEqual(service_status, service_checks.ServiceStatus.OK)
        self.assertEqual(check_info, {})

    def test_critical_and_warning_pass(self):
        def crit_pass():
            return (True, {"info": "crit pass"})

        def warn_pass():
            return (True, {"info": "warn pass"})

        service_checks.CRITICAL_CHECKS = (crit_pass,)
        service_checks.WARNING_CHECKS = (warn_pass,)

        service_status, check_info = service_checks.run_checks()

        self.assertEqual(service_status, service_checks.ServiceStatus.OK)
        self.assertEqual(
            {
                "crit_pass": {"info": "crit pass"},
                "warn_pass": {"info": "warn pass"},
            },
            check_info,
        )

    def test_critical_and_warning_fail(self):
        def crit_fail():
            return (False, {"info": "crit fail"})

        def warn_fail():
            return (False, {"info": "warn fail"})

        service_checks.CRITICAL_CHECKS = (crit_fail,)
        service_checks.WARNING_CHECKS = (warn_fail,)

        service_status, check_info = service_checks.run_checks()

        self.assertEqual(service_status, service_checks.ServiceStatus.CRITICAL)
        self.assertEqual(
            {
                "crit_fail": {"info": "crit fail"},
                "warn_fail": {"info": "warn fail"},
            },
            check_info,
        )

    def test_critical_pass_warning_fail(self):
        def crit_pass():
            return (True, {"info": "crit pass"})

        def warn_fail():
            return (False, {"info": "warn fail"})

        service_checks.CRITICAL_CHECKS = (crit_pass,)
        service_checks.WARNING_CHECKS = (warn_fail,)

        service_status, check_info = service_checks.run_checks()

        self.assertEqual(service_status, service_checks.ServiceStatus.WARNING)
        self.assertEqual(
            {
                "crit_pass": {"info": "crit pass"},
                "warn_fail": {"info": "warn fail"},
            },
            check_info,
        )

    def test_critical_fail_warning_pass(self):
        def crit_fail():
            return (False, {"info": "crit fail"})

        def warn_pass():
            return (True, {"info": "warn pass"})

        service_checks.CRITICAL_CHECKS = (crit_fail,)
        service_checks.WARNING_CHECKS = (warn_pass,)

        service_status, check_info = service_checks.run_checks()

        self.assertEqual(service_status, service_checks.ServiceStatus.CRITICAL)
        self.assertEqual(
            {
                "crit_fail": {"info": "crit fail"},
                "warn_pass": {"info": "warn pass"},
            },
            check_info,
        )

    def test_critical_one_pass_one_fail(self):
        def crit_pass():
            return (True, {"info": "crit pass"})

        def crit_fail():
            return (False, {"info": "crit fail"})

        service_checks.CRITICAL_CHECKS = (crit_fail, crit_pass)
        service_checks.WARNING_CHECKS = ()

        service_status, check_info = service_checks.run_checks()

        self.assertEqual(service_status, service_checks.ServiceStatus.CRITICAL)
        self.assertEqual(
            {
                "crit_fail": {"info": "crit fail"},
                "crit_pass": {"info": "crit pass"},
            },
            check_info,
        )

    def test_warning_one_pass_one_fail(self):
        def warn_pass():
            return (True, {"info": "warn pass"})

        def warn_fail():
            return (False, {"info": "warn fail"})

        service_checks.CRITICAL_CHECKS = ()
        service_checks.WARNING_CHECKS = (warn_pass, warn_fail)

        service_status, check_info = service_checks.run_checks()

        self.assertEqual(service_status, service_checks.ServiceStatus.WARNING)
        self.assertEqual(
            {
                "warn_fail": {"info": "warn fail"},
                "warn_pass": {"info": "warn pass"},
            },
            check_info,
        )
