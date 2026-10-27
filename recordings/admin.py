from django.contrib import admin

from .models import Recording, Transcript


@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "status", "language", "duration_sec", "created_at"]
    list_filter = ["status", "language"]


@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ["recording", "engine"]
