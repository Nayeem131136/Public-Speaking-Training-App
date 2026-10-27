"""Adds the starting settings, filler words and prompts. Safe to run again."""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from appconfig.defaults import DEFAULTS, DESCRIPTIONS
from appconfig.models import AppSetting, FillerWord
from prompts.models import Category, Prompt
from services.fillers import DEFAULT_FILLER_WORDS

# a few Bangla fillers to start with
BANGLA_FILLERS = ["\u0987\u09af\u09bc\u09c7", "\u09ae\u09be\u09a8\u09c7", "\u0986\u09b8\u09b2\u09c7"]

PROMPTS = {
    "Interview": [
        ("Introduce yourself", "Introduce yourself in one minute, as if you are in a job interview.", "easy", 60),
        ("Your biggest strength", "Tell the interviewer about your biggest strength and give one real example.", "medium", 90),
        ("A time you failed", "Describe a time you failed at something and what you learned from it.", "hard", 120),
    ],
    "Presentation": [
        ("Explain your project", "Explain your final-year project to someone who has never studied computer science.", "medium", 120),
        ("Pitch a campus club", "Pitch a new club for your campus. Say why students should join it.", "medium", 120),
        ("Teach a skill", "Teach the audience one useful skill in two minutes.", "hard", 120),
    ],
    "Ice-breaker": [
        ("Meet a new classmate", "You just met a new classmate. Start a conversation and keep it going.", "easy", 60),
        ("Your weekend", "Tell a friend about the best thing that happened to you last weekend.", "easy", 60),
    ],
    "Everyday": [
        ("Recommend a place", "Recommend your favourite place to eat and explain why.", "easy", 60),
        ("Convince a friend", "Convince a friend to start a new habit that you think is worth it.", "medium", 90),
    ],
}

BANGLA_PROMPT = (
    "Everyday",
    "\u09a8\u09bf\u099c\u09c7\u09b0 \u09aa\u09b0\u09bf\u099a\u09af\u09bc",
    "\u09a8\u09bf\u099c\u09c7\u09b0 \u09aa\u09b0\u09bf\u099a\u09af\u09bc \u09a6\u09bf\u09a8 \u098f\u09ac\u0982 \u0986\u09aa\u09a8\u09be\u09b0 \u098f\u0995\u099f\u09bf \u09b2\u0995\u09cd\u09b7\u09cd\u09af\u09c7\u09b0 \u0995\u09a5\u09be \u09ac\u09b2\u09c1\u09a8\u0964",
)


class Command(BaseCommand):
    help = "Add starting settings, filler words and practice prompts."

    def add_arguments(self, parser):
        parser.add_argument("--users", action="store_true", help="also make the demo admin and the demo user")

    def make_users(self):
        # demo accounts for testing and the credentials list, not for a real server
        User = get_user_model()
        accounts = [
            ("admin", os.environ.get("DEMO_ADMIN_PASSWORD", "Admin@Backstage2026"), True),
            ("demo", os.environ.get("DEMO_USER_PASSWORD", "Demo@Backstage2026"), False),
        ]
        for username, password, is_admin in accounts:
            user, _ = User.objects.get_or_create(username=username, defaults={"email": username + "@example.com"})
            user.is_staff = user.is_superuser = is_admin
            user.set_password(password)  # also resets it if someone changed it
            user.save()

    def handle(self, *args, **options):
        for key, value in DEFAULTS.items():
            AppSetting.objects.get_or_create(key=key, defaults={"value": value, "description": DESCRIPTIONS[key]})

        for word in DEFAULT_FILLER_WORDS:
            FillerWord.objects.get_or_create(word=word, language="en", owner=None)
        for word in BANGLA_FILLERS:
            FillerWord.objects.get_or_create(word=word, language="bn", owner=None)

        created = 0
        for category_name, prompts in PROMPTS.items():
            category, _ = Category.objects.get_or_create(name=category_name)
            for title, text, difficulty, seconds in prompts:
                _, was_created = Prompt.objects.get_or_create(
                    category=category, title=title,
                    defaults={"text": text, "difficulty": difficulty, "suggested_seconds": seconds},
                )
                created += was_created

        category_name, title, text = BANGLA_PROMPT
        category, _ = Category.objects.get_or_create(name=category_name)
        _, was_created = Prompt.objects.get_or_create(
            category=category, title=title, defaults={"text": text, "language": "bn", "suggested_seconds": 60}
        )
        created += was_created

        if options["users"]:
            self.make_users()
            self.stdout.write("Demo users ready: admin (admin panel) and demo (normal user).")

        self.stdout.write(self.style.SUCCESS(
            "Done. %s new prompts, %s filler words, %s settings in total."
            % (created, FillerWord.objects.count(), AppSetting.objects.count())
        ))
