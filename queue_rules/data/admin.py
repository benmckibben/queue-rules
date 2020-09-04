from django.contrib import admin

from .models import LastCheckLog, Rule, SongSequenceMember, UserLock


class RuleAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "trigger_song_spotify_id", "is_active")


class SongSequenceMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "rule", "sequence_number", "song_spotify_id")


class LastCheckLogAdmin(admin.ModelAdmin):
    list_display = ("user", "last_checked")


class UserLockAdmin(admin.ModelAdmin):
    list_display = ("user", "created")


admin.site.register(Rule, RuleAdmin)
admin.site.register(SongSequenceMember, SongSequenceMemberAdmin)
admin.site.register(UserLock, UserLockAdmin)
admin.site.register(LastCheckLog, LastCheckLogAdmin)
