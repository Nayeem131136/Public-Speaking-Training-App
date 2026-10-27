from config.testing import ApiTestCase, client_for, make_user
from prompts.models import Category, Prompt


class ProgressApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        category = Category.objects.create(name="Talk")
        self.prompt_a = Prompt.objects.create(category=category, title="A", text="a")
        self.prompt_b = Prompt.objects.create(category=category, title="B", text="b")

    def test_needs_login(self):
        self.assertEqual(self.client.get("/api/v1/progress/").status_code, 401)

    def test_empty(self):
        self.assertEqual(self.api.get("/api/v1/progress/").data, {"results": []})

    def test_attempts_are_listed_oldest_first(self):
        first = self.upload(prompt_id=self.prompt_a.id).data["id"]
        second = self.upload(seconds=20, prompt_id=self.prompt_a.id).data["id"]
        results = self.api.get("/api/v1/progress/").data["results"]
        self.assertEqual([r["recording_id"] for r in results], [first, second])
        self.assertEqual(set(results[0]), {"recording_id", "prompt_id", "created_at", "wpm", "filler_count", "pause_count"})

    def test_filter_by_prompt(self):
        a = self.upload(prompt_id=self.prompt_a.id).data["id"]
        self.upload(prompt_id=self.prompt_b.id)
        results = self.api.get("/api/v1/progress/?prompt_id=%s" % self.prompt_a.id).data["results"]
        self.assertEqual([r["recording_id"] for r in results], [a])

    def test_bad_prompt_id(self):
        self.assertEqual(self.api.get("/api/v1/progress/?prompt_id=x").status_code, 400)

    def test_only_my_attempts(self):
        self.upload()
        other = client_for(make_user("bob"))
        self.assertEqual(other.get("/api/v1/progress/").data, {"results": []})
