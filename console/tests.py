from django.contrib.staticfiles import finders
from django.test import TestCase


class ConsolePageTests(TestCase):
    def test_home_page_opens(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Backstage")
        self.assertContains(response, "console/app.js")

    def test_every_script_and_style_file_exists(self):
        for name in ["api.js", "app.js", "recorder.js", "pace_view.js", "filler_view.js", "console.css", "icon.png"]:
            self.assertIsNotNone(finders.find("console/" + name), name)
