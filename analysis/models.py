from django.db import models


class AnalysisResult(models.Model):
    """The numbers for one recording."""

    recording = models.OneToOneField("recordings.Recording", on_delete=models.CASCADE, related_name="analysis")
    total_words = models.PositiveIntegerField(default=0)
    speaking_seconds = models.FloatField(default=0)
    wpm = models.FloatField(default=0)
    filler_count = models.PositiveIntegerField(default=0)
    pause_count = models.PositiveIntegerField(default=0)
    longest_pause_sec = models.FloatField(default=0)
    pacing_segments = models.JSONField(default=list, help_text="List of {start_sec, end_sec, wpm}")
    settings_snapshot = models.JSONField(default=dict, help_text="The thresholds used for this result")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "Analysis of recording %s" % self.recording_id


class FillerOccurrence(models.Model):
    analysis = models.ForeignKey(AnalysisResult, on_delete=models.CASCADE, related_name="filler_occurrences")
    word = models.CharField(max_length=100)
    start_sec = models.FloatField()
    end_sec = models.FloatField()

    class Meta:
        ordering = ["start_sec"]


class PauseEvent(models.Model):
    KINDS = [("short", "Short"), ("dramatic", "Dramatic"), ("long", "Long")]

    analysis = models.ForeignKey(AnalysisResult, on_delete=models.CASCADE, related_name="pause_events")
    start_sec = models.FloatField()
    end_sec = models.FloatField()
    duration_sec = models.FloatField()
    kind = models.CharField(max_length=10, choices=KINDS)

    class Meta:
        ordering = ["start_sec"]
