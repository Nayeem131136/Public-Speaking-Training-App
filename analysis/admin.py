from django.contrib import admin

from .models import AnalysisResult, FillerOccurrence, PauseEvent


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ["recording", "wpm", "filler_count", "pause_count", "created_at"]


admin.site.register(FillerOccurrence)
admin.site.register(PauseEvent)
