from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Prompt(models.Model):
    DIFFICULTIES = [("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")]
    LANGUAGES = [("en", "English"), ("bn", "Bangla")]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="prompts")
    title = models.CharField(max_length=120)
    text = models.TextField(help_text="The topic or question the user speaks about")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTIES, default="easy")
    suggested_seconds = models.PositiveIntegerField(null=True, blank=True)
    language = models.CharField(max_length=5, choices=LANGUAGES, default="en")
    is_active = models.BooleanField(default=True, help_text="Untick to hide it from users")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title
