from rest_framework.test import APITestCase

from config.testing import client_for, make_user

from .models import Category, Prompt


class PromptApiTests(APITestCase):
    def setUp(self):
        self.interview = Category.objects.create(name="Interview")
        self.talk = Category.objects.create(name="Presentation")
        self.p1 = Prompt.objects.create(category=self.interview, title="Introduce yourself", text="Say who you are")
        self.p2 = Prompt.objects.create(category=self.talk, title="Pitch a club", text="Explain the idea")
        self.p3 = Prompt.objects.create(category=self.talk, title="Hidden one", text="x", is_active=False)
        self.p4 = Prompt.objects.create(category=self.talk, title="Bangla one", text="y", language="bn")
        self.api = client_for(make_user())

    def test_needs_login(self):
        self.assertEqual(self.client.get("/api/v1/prompts/").status_code, 401)

    def test_list_hides_inactive_prompts(self):
        response = self.api.get("/api/v1/prompts/")
        titles = [p["title"] for p in response.data["results"]]
        self.assertEqual(response.data["count"], 3)
        self.assertNotIn("Hidden one", titles)

    def test_filter_by_category(self):
        response = self.api.get("/api/v1/prompts/?category=%s" % self.interview.id)
        self.assertEqual([p["title"] for p in response.data["results"]], ["Introduce yourself"])

    def test_filter_by_language(self):
        response = self.api.get("/api/v1/prompts/?language=bn")
        self.assertEqual([p["title"] for p in response.data["results"]], ["Bangla one"])

    def test_search(self):
        response = self.api.get("/api/v1/prompts/?search=club")
        self.assertEqual([p["title"] for p in response.data["results"]], ["Pitch a club"])

    def test_detail_has_category_name(self):
        response = self.api.get("/api/v1/prompts/%s/" % self.p1.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category_name"], "Interview")

    def test_inactive_prompt_detail_is_not_found(self):
        response = self.api.get("/api/v1/prompts/%s/" % self.p3.id)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["code"], "not_found")

    def test_categories(self):
        response = self.api.get("/api/v1/categories/")
        self.assertEqual([c["name"] for c in response.data["results"]], ["Interview", "Presentation"])

    def test_page_size(self):
        response = self.api.get("/api/v1/prompts/?page_size=1")
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["count"], 3)
