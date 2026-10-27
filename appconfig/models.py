from django.conf import settings
from django.db import models


class FillerWord(models.Model):
    """A filler word. No owner means global, otherwise it belongs to one user."""

    LANGUAGES = [("en", "English"), ("bn", "Bangla")]

    word = models.CharField(max_length=100)
    language = models.CharField(max_length=5, choices=LANGUAGES, default="en")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="filler_words"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["word"]
        constraints = [models.UniqueConstraint(fields=["word", "language", "owner"], name="unique_filler_per_owner")]

    def save(self, *args, **kwargs):
        self.word = self.word.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.word


class AppSetting(models.Model):
    """A value admins can change without touching code, e.g. the target pace."""

    key = models.CharField(max_length=80, primary_key=True)
    value = models.JSONField()
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return "%s = %s" % (self.key, self.value)
