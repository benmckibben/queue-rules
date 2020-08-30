from datetime import datetime, timezone
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from freezegun import freeze_time

from api.serializers import RuleSerializer, SongSequenceMemberSerializer
from data.models import Rule, SongSequenceMember


class TestSongSequenceMemberSerializer(TestCase):
    def setUp(self):
        self.test_user = User.objects.create(username="test1")
        self.test_rule = Rule.objects.create(
            owner=self.test_user, trigger_song_spotify_id="foo"
        )

    def test_serialize(self):
        seq_member = SongSequenceMember.objects.create(
            name="Ram Ranch",
            song_spotify_id="bar",
            rule=self.test_rule,
            sequence_number=100,
        )
        serializer = SongSequenceMemberSerializer(seq_member)
        self.assertEqual(
            serializer.data,
            {
                "id": seq_member.id,
                "name": "Ram Ranch",
                "song_spotify_id": "bar",
                "sequence_number": 100,
            },
        )


class TestRuleSerializer(TestCase):
    def setUp(self):
        self.test_user = User.objects.create(username="test1")

    @freeze_time("2020-08-15")
    def test_serialize_no_sequence(self):
        rule = Rule.objects.create(
            name="Ram Ranch",
            owner=self.test_user,
            trigger_song_spotify_id="foo",
            is_active=False,
        )
        serializer = RuleSerializer(rule)
        self.assertEqual(
            serializer.data,
            {
                "id": rule.id,
                "name": "Ram Ranch",
                "created": "2020-08-15T00:00:00Z",
                "trigger_song_spotify_id": "foo",
                "is_active": False,
                "song_sequence": [],
            },
        )

    @freeze_time("2020-08-15")
    def test_serialize_with_sequence(self):
        rule = Rule.objects.create(
            name="Porter Robinson - Get Your Wish",
            owner=self.test_user,
            trigger_song_spotify_id="foo",
            is_active=False,
        )
        seq_1 = SongSequenceMember.objects.create(
            name="Porter Robinson, Anamanaguchi - Get Your Wish (Anamanaguchi Remix)",
            rule=rule,
            song_spotify_id="bar",
            sequence_number=2,
        )
        seq_2 = SongSequenceMember.objects.create(
            name="Porter Robinson - Get Your Wish (DJ NOT PORTER ROBINSON Remix)",
            rule=rule,
            song_spotify_id="baz",
            sequence_number=0,
        )
        serializer = RuleSerializer(rule)
        self.assertEqual(
            serializer.data,
            {
                "id": rule.id,
                "name": "Porter Robinson - Get Your Wish",
                "created": "2020-08-15T00:00:00Z",
                "trigger_song_spotify_id": "foo",
                "is_active": False,
                "song_sequence": [
                    {
                        "id": seq_2.id,
                        "name": "Porter Robinson - Get Your Wish (DJ NOT PORTER ROBINSON Remix)",  # noqa: E501
                        "song_spotify_id": "baz",
                        "sequence_number": 0,
                    },
                    {
                        "id": seq_1.id,
                        "name": "Porter Robinson, Anamanaguchi - Get Your Wish (Anamanaguchi Remix)",  # noqa: E501
                        "song_spotify_id": "bar",
                        "sequence_number": 2,
                    },
                ],
            },
        )

    @freeze_time("2020-08-15")
    @mock.patch("api.serializers.Rule.set_name")
    def test_create_no_sequence(self, mock_set_name):
        serializer = RuleSerializer(
            data={
                "trigger_song_spotify_id": "foo",
                "is_active": False,
                "song_sequence": [],
            }
        )
        self.assertTrue(serializer.is_valid())

        serializer.save(owner=self.test_user)
        rule = Rule.objects.get()

        self.assertEqual(rule.owner, self.test_user)
        self.assertEqual(rule.created, datetime(2020, 8, 15, tzinfo=timezone.utc))
        self.assertEqual(rule.trigger_song_spotify_id, "foo")
        self.assertFalse(rule.is_active)
        self.assertIsNone(rule.last_applied)
        self.assertEqual(len(rule.get_song_sequence()), 0)
        mock_set_name.assert_called_once()

    @mock.patch("api.serializers.SongSequenceMember.set_name")
    @mock.patch("api.serializers.Rule.set_name")
    @freeze_time("2020-08-15")
    def test_create_with_sequence(self, mock_rule_set_name, mock_ssm_set_name):
        serializer = RuleSerializer(
            data={
                "trigger_song_spotify_id": "foo",
                "is_active": False,
                "song_sequence": [
                    {"song_spotify_id": "baz", "sequence_number": 2},
                    {"song_spotify_id": "bar", "sequence_number": 0},
                ],
            }
        )
        self.assertTrue(serializer.is_valid())

        serializer.save(owner=self.test_user)
        rule = Rule.objects.get()

        self.assertEqual(rule.owner, self.test_user)
        self.assertEqual(rule.created, datetime(2020, 8, 15, tzinfo=timezone.utc))
        self.assertEqual(rule.trigger_song_spotify_id, "foo")
        self.assertFalse(rule.is_active)
        self.assertIsNone(rule.last_applied)
        mock_rule_set_name.assert_called_once()

        sequence = rule.get_song_sequence()

        self.assertEqual(len(sequence), 2)
        self.assertEqual(len(mock_ssm_set_name.mock_calls), 2)

        self.assertEqual(sequence[0].song_spotify_id, "bar")
        self.assertEqual(sequence[0].sequence_number, 0)

        self.assertEqual(sequence[1].song_spotify_id, "baz")
        self.assertEqual(sequence[1].sequence_number, 2)

    @mock.patch("api.serializers.SongSequenceMember.set_name")
    @mock.patch("api.serializers.Rule.set_name")
    @freeze_time("2020-08-15")
    def test_update_remove_sequence(self, mock_rule_set_name, mock_ssm_set_name):
        rule = Rule.objects.create(
            owner=self.test_user,
            trigger_song_spotify_id="foo",
            is_active=True,
        )
        SongSequenceMember.objects.create(
            rule=rule,
            song_spotify_id="bar",
            sequence_number=2,
        )

        # Sanity check that we have a sequence.
        self.assertEqual(len(rule.get_song_sequence()), 1)

        serializer = RuleSerializer(
            rule,
            data={
                "trigger_song_spotify_id": "foo2",
                "is_active": False,
                "song_sequence": [],
            },
        )
        self.assertTrue(serializer.is_valid())

        serializer.save()
        rule.refresh_from_db()

        self.assertEqual(rule.trigger_song_spotify_id, "foo2")
        self.assertFalse(rule.is_active)
        mock_rule_set_name.assert_called_once()

        self.assertEqual(len(rule.get_song_sequence()), 0)
        mock_ssm_set_name.assert_not_called()

    @mock.patch("api.serializers.SongSequenceMember.set_name")
    @mock.patch("api.serializers.Rule.set_name")
    @freeze_time("2020-08-15")
    def test_update_update_sequence(self, mock_rule_set_name, mock_ssm_set_name):
        rule = Rule.objects.create(
            owner=self.test_user,
            trigger_song_spotify_id="foo",
            is_active=True,
        )
        SongSequenceMember.objects.create(
            rule=rule,
            song_spotify_id="bar",
            sequence_number=2,
        )

        # Sanity check that we have a sequence.
        self.assertEqual(len(rule.get_song_sequence()), 1)

        serializer = RuleSerializer(
            rule,
            data={
                "trigger_song_spotify_id": "foo2",
                "is_active": False,
                "song_sequence": [{"song_spotify_id": "baz", "sequence_number": 100}],
            },
        )
        self.assertTrue(serializer.is_valid())

        serializer.save()
        rule.refresh_from_db()

        self.assertEqual(rule.trigger_song_spotify_id, "foo2")
        self.assertFalse(rule.is_active)
        mock_rule_set_name.assert_called_once()

        sequence = rule.get_song_sequence()
        self.assertEqual(len(sequence), 1)
        self.assertEqual(sequence[0].song_spotify_id, "baz")
        self.assertEqual(sequence[0].sequence_number, 100)
        mock_ssm_set_name.assert_called_once()

    @mock.patch("api.serializers.SongSequenceMember.set_name")
    @mock.patch("api.serializers.Rule.set_name")
    @freeze_time("2020-08-15")
    def test_update_no_is_active(self, mock_rule_set_name, mock_ssm_set_name):
        rule = Rule.objects.create(
            owner=self.test_user,
            trigger_song_spotify_id="foo",
            is_active=False,
        )

        serializer = RuleSerializer(
            rule, data={"trigger_song_spotify_id": "foo2", "song_sequence": []}
        )
        self.assertTrue(serializer.is_valid())

        serializer.save()
        rule.refresh_from_db()

        self.assertFalse(rule.is_active)
        mock_rule_set_name.assert_called_once()
        mock_ssm_set_name.assert_not_called()
