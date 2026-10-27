from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from appconfig.models import AppSetting, FillerWord
from prompts.models import Prompt


class SeedDemoTests(TestCase):
    def seed(self, *args):
        call_command("seed_demo", *args, stdout=StringIO())

    def test_seeding_twice_does_not_make_duplicates(self):
        self.seed()
        counts = (Prompt.objects.count(), FillerWord.objects.count(), AppSetting.objects.count())
        self.seed()
        self.assertEqual(counts, (Prompt.objects.count(), FillerWord.objects.count(), AppSetting.objects.count()))
        self.assertGreater(counts[0], 5)

    def test_users_are_only_made_when_asked(self):
        self.seed()
        self.assertFalse(get_user_model().objects.filter(username__in=["admin", "demo"]).exists())

    def test_demo_users(self):
        self.seed("--users")
        User = get_user_model()
        admin, demo = User.objects.get(username="admin"), User.objects.get(username="demo")
        self.assertTrue(admin.is_staff and admin.is_superuser)
        self.assertFalse(demo.is_staff or demo.is_superuser)
        response = self.client.post("/api/v1/auth/login/", {"username": "demo", "password": "Demo@Backstage2026"})
        self.assertEqual(response.status_code, 200)

    def test_running_it_again_resets_the_demo_passwords(self):
        self.seed("--users")
        user = get_user_model().objects.get(username="demo")
        user.set_password("changed-by-someone")
        user.save()
        self.seed("--users")
        user.refresh_from_db()
        self.assertTrue(user.check_password("Demo@Backstage2026"))
