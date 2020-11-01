import logging
from unittest import mock

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from freezegun import freeze_time
from rest_framework.test import APIClient

from api.service_checks import ServiceStatus
from data.exceptions import BadSpotifyTrackID
from data.models import Rule, SongSequenceMember


class TestRuleList(TestCase):
    def setUp(self):
        # Squelch logging for these tests.
        logging.disable(logging.CRITICAL)

        self.test_user_1 = User.objects.create(username="test1")
        self.test_user_2 = User.objects.create(username="test2")
        self.test_user_3 = User.objects.create(username="test3")

        with freeze_time("2020-08-15"):
            self.test_rule_1 = Rule.objects.create(
                owner=self.test_user_1, trigger_song_spotify_id="foo"
            )

        with freeze_time("2020-08-17"):
            self.test_rule_2 = Rule.objects.create(
                owner=self.test_user_2, trigger_song_spotify_id="bar"
            )
            self.test_rule_3 = Rule.objects.create(
                owner=self.test_user_1, trigger_song_spotify_id="baz"
            )

    def tearDown(self):
        # Reenable logging when tests finish.
        logging.disable(logging.NOTSET)

    def test_get_only_owner_rules(self):
        client = APIClient()
        client.force_authenticate(self.test_user_1)

        response = client.get(reverse("rule-list"))

        # Make sure that we only got two rules, the ones owned by test_user_1.
        self.assertEqual(len(response.data), 2)

        # Make sure that they are ordered by descending date created.
        self.assertEqual(response.data[0]["id"], self.test_rule_3.id)
        self.assertEqual(response.data[1]["id"], self.test_rule_1.id)

    def test_no_rules(self):
        client = APIClient()
        client.force_authenticate(self.test_user_3)

        response = client.get(reverse("rule-list"))
        self.assertEqual(response.data, [])

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get(reverse("rule-list"))
        self.assertEqual(response.status_code, 403)


class TestRuleDetail(TestCase):
    def setUp(self):
        # Squelch logging for these tests.
        logging.disable(logging.CRITICAL)

        self.test_user_1 = User.objects.create(username="test1")
        self.test_user_2 = User.objects.create(username="test2")

        self.test_rule_1 = Rule.objects.create(
            owner=self.test_user_1,
            trigger_song_spotify_id="foo",
            is_active=True,
        )

    def tearDown(self):
        # Reenable logging when tests finish.
        logging.disable(logging.NOTSET)

    def test_get(self):
        client = APIClient()
        client.force_authenticate(self.test_user_1)

        response = client.get(
            reverse("rule-detail", kwargs={"pk": self.test_rule_1.id})
        )
        self.assertEqual(response.status_code, 200)

    def test_get_someone_elses_rule(self):
        client = APIClient()
        client.force_authenticate(self.test_user_2)

        response = client.get(
            reverse("rule-detail", kwargs={"pk": self.test_rule_1.id})
        )
        self.assertEqual(response.status_code, 403)

    def test_get_unauthenticated(self):
        client = APIClient()

        response = client.get(
            reverse("rule-detail", kwargs={"pk": self.test_rule_1.id})
        )
        self.assertEqual(response.status_code, 403)

    def test_get_not_found_authenticated(self):
        client = APIClient()
        client.force_authenticate(self.test_user_1)

        rule_id = self.test_rule_1.id
        self.test_rule_1.delete()

        response = client.get(reverse("rule-detail", kwargs={"pk": rule_id}))
        self.assertEqual(response.status_code, 404)

    def test_get_not_found_unauthenticated(self):
        client = APIClient()

        rule_id = self.test_rule_1.id
        self.test_rule_1.delete()

        response = client.get(reverse("rule-detail", kwargs={"pk": rule_id}))
        self.assertEqual(response.status_code, 403)

    @mock.patch("api.serializers.Rule.set_name")
    def test_put(self, mock_set_name):
        client = APIClient()
        client.force_authenticate(self.test_user_1)

        response = client.put(
            reverse("rule-detail", kwargs={"pk": self.test_rule_1.id}),
            {
                "trigger_song_spotify_id": "bar",
                "song_sequence": [],
                "is_active": False,
            },
            format="json",
        )
        self.test_rule_1.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.test_rule_1.trigger_song_spotify_id, "bar")
        self.assertFalse(self.test_rule_1.is_active)
        mock_set_name.assert_called_once()

    @mock.patch("api.serializers.Rule.set_name")
    def test_put_bad_track(self, mock_set_name):
        client = APIClient()
        client.force_authenticate(self.test_user_1)

        mock_set_name.side_effect = BadSpotifyTrackID("terrible_track_id")

        response = client.put(
            reverse("rule-detail", kwargs={"pk": self.test_rule_1.id}),
            {
                "trigger_song_spotify_id": "terrible_track_id",
                "song_sequence": [],
                "is_active": False,
            },
            format="json",
        )
        self.test_rule_1.refresh_from_db()

        self.assertEqual(response.status_code, 400)
        self.assertIn("terrible_track_id", response.data[0])
        mock_set_name.assert_called_once()

        # Ensure atomicity
        self.assertEqual(self.test_rule_1.trigger_song_spotify_id, "foo")
        self.assertTrue(self.test_rule_1.is_active)

    def test_put_someone_elses_rule(self):
        client = APIClient()
        client.force_authenticate(self.test_user_2)

        response = client.put(
            reverse("rule-detail", kwargs={"pk": self.test_rule_1.id}),
            {
                "trigger_song_spotify_id": "bar",
                "song_sequence": [],
                "is_active": False,
            },
            format="json",
        )
        self.test_rule_1.refresh_from_db()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.test_rule_1.trigger_song_spotify_id, "foo")
        self.assertTrue(self.test_rule_1.is_active)

    def test_put_unauthenticated(self):
        client = APIClient()

        response = client.put(
            reverse("rule-detail", kwargs={"pk": self.test_rule_1.id}),
            {
                "trigger_song_spotify_id": "bar",
                "song_sequence": [],
                "is_active": False,
            },
            format="json",
        )
        self.test_rule_1.refresh_from_db()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.test_rule_1.trigger_song_spotify_id, "foo")
        self.assertTrue(self.test_rule_1.is_active)

    def test_delete(self):
        client = APIClient()
        client.force_authenticate(self.test_user_1)

        response = client.delete(
            reverse("rule-detail", kwargs={"pk": self.test_rule_1.id})
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(Rule.objects.count(), 0)

    def test_delete_someone_elses_rule(self):
        client = APIClient()
        client.force_authenticate(self.test_user_2)

        response = client.delete(
            reverse("rule-detail", kwargs={"pk": self.test_rule_1.id})
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Rule.objects.count(), 1)

    def test_delete_unauthenticated(self):
        client = APIClient()

        response = client.delete(
            reverse("rule-detail", kwargs={"pk": self.test_rule_1.id})
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Rule.objects.count(), 1)


class TestCreateRule(TestCase):
    def setUp(self):
        # Squelch logging for these tests.
        logging.disable(logging.CRITICAL)

        self.test_user_1 = User.objects.create(username="test1")

    def tearDown(self):
        # Reenable logging when tests finish.
        logging.disable(logging.NOTSET)

    def test_get(self):
        client = APIClient()
        client.force_authenticate(self.test_user_1)

        response = client.get(reverse("rule-create"))
        self.assertEqual(response.status_code, 405)

    @mock.patch("api.serializers.Rule.set_name")
    def test_post(self, mock_set_name):
        client = APIClient()
        client.force_authenticate(self.test_user_1)

        response = client.post(
            reverse("rule-create"),
            {
                "trigger_song_spotify_id": "foo",
                "song_sequence": [],
                "is_active": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        new_rule = Rule.objects.get()  # Implicitly tests there's only one Rule
        self.assertEqual(new_rule.trigger_song_spotify_id, "foo")
        self.assertFalse(new_rule.is_active)
        mock_set_name.assert_called_once()

    @mock.patch("api.serializers.Rule.set_name")
    def test_post_bad_track(self, mock_set_name):
        client = APIClient()
        client.force_authenticate(self.test_user_1)

        mock_set_name.side_effect = BadSpotifyTrackID("terrible_track_id")

        response = client.post(
            reverse("rule-create"),
            {
                "trigger_song_spotify_id": "terrible_track_id",
                "song_sequence": [],
                "is_active": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("terrible_track_id", response.data[0])
        mock_set_name.assert_called_once()

        # Ensure atomicity
        self.assertEqual(Rule.objects.count(), 0)

    def test_post_duplicate_rule(self):
        client = APIClient()
        client.force_authenticate(self.test_user_1)

        Rule.objects.create(owner=self.test_user_1, trigger_song_spotify_id="dupe")

        response = client.post(
            reverse("rule-create"),
            {
                "trigger_song_spotify_id": "dupe",
                "song_sequence": [],
                "is_active": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_post_unauthenticated(self):
        client = APIClient()

        response = client.post(
            reverse("rule-create"),
            {
                "trigger_song_spotify_id": "foo",
                "song_sequence": [],
                "is_active": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Rule.objects.count(), 0)


class TestServiceStatus(SimpleTestCase):
    def setUp(self):
        # Squelch logging for these tests.
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        # Reenable logging when tests finish.
        logging.disable(logging.NOTSET)

    @mock.patch("api.views.run_checks")
    def test_ok(self, mock_run_checks):
        mock_run_checks.return_value = (
            ServiceStatus.OK,
            {"checks": "pass"},
        )

        client = APIClient()
        response = client.get(reverse("service-status"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                "status": "OK",
                "info": {"checks": "pass"},
            },
        )

    @mock.patch("api.views.run_checks")
    def test_warning(self, mock_run_checks):
        mock_run_checks.return_value = (
            ServiceStatus.WARNING,
            {"checks": "warning"},
        )

        client = APIClient()
        response = client.get(reverse("service-status"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                "status": "WARNING",
                "info": {"checks": "warning"},
            },
        )

    @mock.patch("api.views.run_checks")
    def test_critical(self, mock_run_checks):
        mock_run_checks.return_value = (
            ServiceStatus.CRITICAL,
            {"checks": "critical"},
        )

        client = APIClient()
        response = client.get(reverse("service-status"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.data,
            {
                "status": "CRITICAL",
                "info": {"checks": "critical"},
            },
        )

    @mock.patch("api.views.run_checks")
    def test_bad_status(self, mock_run_checks):
        mock_run_checks.return_value = ("???", {})

        client = APIClient()
        with self.assertRaises(ValueError):
            client.get(reverse("service-status"))


class TestLogout(TestCase):
    def setUp(self):
        # Squelch logging for these tests.
        logging.disable(logging.CRITICAL)

        self.test_user = User.objects.create(username="test")

    def tearDown(self):
        # Reenable logging when tests finish.
        logging.disable(logging.NOTSET)

    def test_logout(self):
        client = APIClient()
        client.force_login(self.test_user)

        response = client.post(reverse("logout"))
        self.assertEqual(response.status_code, 200)

        # Try getting a view that needs auth.
        response = client.get(reverse("rule-list"))
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated(self):
        client = APIClient()

        response = client.post(reverse("logout"))
        self.assertEqual(response.status_code, 403)


class TestDeleteAccount(TestCase):
    def setUp(self):
        # Squelch logging for these tests.
        logging.disable(logging.CRITICAL)

        self.test_user = User.objects.create(username="test")
        self.test_rule = Rule.objects.create(
            owner=self.test_user, trigger_song_spotify_id="foo"
        )
        self.test_ssm = SongSequenceMember.objects.create(
            rule=self.test_rule, song_spotify_id="bar", sequence_number=0
        )

    def tearDown(self):
        # Reenable logging when tests finish.
        logging.disable(logging.NOTSET)

    def test_delete(self):
        client = APIClient()
        client.force_login(self.test_user)

        response = client.delete(reverse("delete-account"))
        self.assertEqual(response.status_code, 200)

        # Try getting a view that needs auth.
        response = client.get(reverse("rule-list"))
        self.assertEqual(response.status_code, 403)

        # Make sure that the user was deleted.
        self.assertEqual(User.objects.count(), 0)

        # Also test that the user's data was deleted.
        self.assertEqual(Rule.objects.count(), 0)
        self.assertEqual(SongSequenceMember.objects.count(), 0)

    def test_unauthenticated(self):
        client = APIClient()

        response = client.post(reverse("delete-account"))
        self.assertEqual(response.status_code, 403)
