from django.contrib import admin

from .models import Rule, SongSequenceMember


class RuleAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "trigger_song_spotify_id", "is_active")


class SongSequenceMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "rule", "sequence_number", "song_spotify_id")


admin.site.register(Rule, RuleAdmin)
admin.site.register(SongSequenceMember, SongSequenceMemberAdmin)
