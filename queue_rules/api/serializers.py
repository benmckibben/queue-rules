from django.db.transaction import atomic
from rest_framework import serializers

from data.models import Rule, SongSequenceMember


class SongSequenceMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = SongSequenceMember
        fields = ["id", "name", "song_spotify_id", "sequence_number"]


class RuleSerializer(serializers.ModelSerializer):
    song_sequence = SongSequenceMemberSerializer(many=True)

    class Meta:
        model = Rule
        fields = [
            "id",
            "name",
            "created",
            "trigger_song_spotify_id",
            "is_active",
            "song_sequence",
        ]

    def create(self, validated_data):
        sequence_data = validated_data.pop("song_sequence")

        with atomic():
            rule = Rule.objects.create(**validated_data)
            rule.set_name()

            for sequence_member_data in sequence_data:
                member = SongSequenceMember.objects.create(
                    rule=rule, **sequence_member_data
                )
                member.set_name()

        return rule

    def update(self, instance, validated_data):
        sequence_data = validated_data.pop("song_sequence")

        with atomic():
            instance.trigger_song_spotify_id = validated_data["trigger_song_spotify_id"]

            if validated_data.get("is_active", None) is not None:
                instance.is_active = validated_data["is_active"]

            instance.save()
            instance.set_name()

            SongSequenceMember.objects.filter(rule=instance).delete()

            for sequence_member_data in sequence_data:
                member = SongSequenceMember.objects.create(
                    rule=instance, **sequence_member_data
                )
                member.set_name()

        return instance
