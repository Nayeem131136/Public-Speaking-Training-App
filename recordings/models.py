from django.conf import settings
from django.db import models


class Recording(models.Model):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    STATUSES = [(PROCESSING, "Processing"), (COMPLETED, "Completed"), (FAILED, "Failed")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recordings")
    prompt = models.ForeignKey(
        "prompts.Prompt", on_delete=models.SET_NULL, null=True, blank=True, related_name="recordings"
    )
    status = models.CharField(max_length=12, choices=STATUSES, default=PROCESSING)
    language = models.CharField(max_length=5, default="en")
    duration_sec = models.FloatField(null=True, blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return "Recording %s (%s)" % (self.pk, self.status)


class Transcript(models.Model):
    recording = models.OneToOneField(Recording, on_delete=models.CASCADE, related_name="transcript")
    full_text = models.TextField(blank=True)
    words = models.JSONField(default=list, help_text="List of {word, start, end}, times in seconds")
    engine = models.CharField(max_length=30, blank=True, help_text="faster-whisper or mock")

    def __str__(self):
        return "Transcript of recording %s" % self.recording_id
