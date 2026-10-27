from appconfig.models import FillerWord
from appconfig.word_lists import get_active_filler_words
from config.testing import ApiTestCase, client_for, make_user
from services.fillers import DEFAULT_FILLER_WORDS


class FillerWordApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.bob = make_user("bob")
        self.admin_user = make_user("boss", staff=True)
        self.admin = client_for(self.admin_user)
        self.global_um = FillerWord.objects.create(word="um", language="en")
        self.bob_word = FillerWord.objects.create(word="whatever", language="en", owner=self.bob)

    def words(self, client=None):
        response = (client or self.api).get("/api/v1/filler-words/")
        return {w["word"]: w for w in response.data["results"]}

    def test_needs_login(self):
        self.assertEqual(self.client.get("/api/v1/filler-words/").status_code, 401)

    def test_list_is_global_words_plus_my_own_only(self):
        mine = FillerWord.objects.create(word="basically", language="en", owner=self.user)
        words = self.words()
        self.assertEqual(set(words), {"um", "basically"})
        self.assertEqual(words["um"]["scope"], "global")
        self.assertEqual(words["basically"]["scope"], "personal")
        self.assertNotIn("whatever", words)
        self.assertEqual(mine.owner, self.user)

    def test_filter_by_language(self):
        FillerWord.objects.create(word="ইয়ে", language="bn")
        response = self.api.get("/api/v1/filler-words/?language=bn")
        self.assertEqual([w["word"] for w in response.data["results"]], ["ইয়ে"])

    def test_add_a_personal_word(self):
        response = self.api.post("/api/v1/filler-words/", {"word": "  Literally "}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["word"], "literally")
        self.assertEqual(response.data["scope"], "personal")
        self.assertEqual(FillerWord.objects.get(word="literally").owner, self.user)

    def test_normal_user_cannot_add_a_global_word(self):
        response = self.api.post("/api/v1/filler-words/", {"word": "kinda", "scope": "global"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(FillerWord.objects.filter(word="kinda").exists())

    def test_admin_adds_a_global_word(self):
        response = self.admin.post("/api/v1/filler-words/", {"word": "kinda", "scope": "global"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["scope"], "global")
        self.assertIsNone(FillerWord.objects.get(word="kinda").owner)
        self.assertIn("kinda", self.words())  # everyone sees it

    def test_duplicates_are_rejected(self):
        self.api.post("/api/v1/filler-words/", {"word": "literally"}, format="json")
        again = self.api.post("/api/v1/filler-words/", {"word": "LITERALLY"}, format="json")
        self.assertEqual(again.status_code, 400)
        global_again = self.admin.post("/api/v1/filler-words/", {"word": "um", "scope": "global"}, format="json")
        self.assertEqual(global_again.status_code, 400)

    def test_the_same_word_can_be_global_and_personal(self):
        response = self.api.post("/api/v1/filler-words/", {"word": "um"}, format="json")
        self.assertEqual(response.status_code, 201)

    def test_empty_word_is_rejected(self):
        self.assertEqual(self.api.post("/api/v1/filler-words/", {"word": "   "}, format="json").status_code, 400)

    def test_edit_and_switch_off_my_word(self):
        created = self.api.post("/api/v1/filler-words/", {"word": "literally"}, format="json").data
        response = self.api.patch("/api/v1/filler-words/%s/" % created["id"], {"is_active": False}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_active"])
        self.assertNotIn("literally", get_active_filler_words(self.user, "en"))

    def test_delete_my_word(self):
        created = self.api.post("/api/v1/filler-words/", {"word": "literally"}, format="json").data
        self.assertEqual(self.api.delete("/api/v1/filler-words/%s/" % created["id"]).status_code, 204)
        self.assertFalse(FillerWord.objects.filter(id=created["id"]).exists())

    def test_normal_user_cannot_change_or_delete_a_global_word(self):
        url = "/api/v1/filler-words/%s/" % self.global_um.id
        self.assertEqual(self.api.patch(url, {"is_active": False}, format="json").status_code, 403)
        self.assertEqual(self.api.delete(url).status_code, 403)
        self.assertTrue(FillerWord.objects.filter(id=self.global_um.id).exists())

    def test_admin_can_change_and_delete_a_global_word(self):
        url = "/api/v1/filler-words/%s/" % self.global_um.id
        self.assertEqual(self.admin.patch(url, {"is_active": False}, format="json").status_code, 200)
        self.assertEqual(self.admin.delete(url).status_code, 204)

    def test_someone_elses_personal_word_is_not_found(self):
        url = "/api/v1/filler-words/%s/" % self.bob_word.id
        self.assertEqual(self.api.get(url).status_code, 404)
        self.assertEqual(self.api.delete(url).status_code, 404)


class ActiveWordsTests(ApiTestCase):
    def test_empty_table_falls_back_to_the_built_in_list(self):
        self.assertEqual(get_active_filler_words(self.user, "en"), sorted(DEFAULT_FILLER_WORDS))
        self.assertEqual(get_active_filler_words(self.user, "bn"), [])

    def test_personal_words_do_not_remove_the_built_in_list(self):
        FillerWord.objects.create(word="literally", language="en", owner=self.user)
        words = get_active_filler_words(self.user, "en")
        self.assertIn("literally", words)
        self.assertIn("um", words)

    def test_inactive_and_other_language_words_are_left_out(self):
        FillerWord.objects.create(word="um", language="en")
        FillerWord.objects.create(word="uh", language="en", is_active=False)
        FillerWord.objects.create(word="ইয়ে", language="bn")
        self.assertEqual(get_active_filler_words(self.user, "en"), ["um"])
        self.assertEqual(get_active_filler_words(self.user, "bn"), ["ইয়ে"])

    def test_works_without_a_user(self):
        FillerWord.objects.create(word="um", language="en")
        FillerWord.objects.create(word="mine", language="en", owner=self.user)
        self.assertEqual(get_active_filler_words(None, "en"), ["um"])
        self.assertEqual(get_active_filler_words(self.user, "en"), ["mine", "um"])


class FillerWordsInAnalysisTests(ApiTestCase):
    def filler_count(self, recording_id):
        return self.api.get("/api/v1/recordings/%s/analysis/" % recording_id).data["summary"]["filler_count"]

    def test_my_own_filler_words_are_counted_in_my_recordings(self):
        before = self.filler_count(self.upload().data["id"])
        self.api.post("/api/v1/filler-words/", {"word": "practice"}, format="json")  # the mock speech says it
        after = self.filler_count(self.upload().data["id"])
        self.assertGreater(after, before)

    def test_other_users_do_not_get_my_words(self):
        self.api.post("/api/v1/filler-words/", {"word": "practice"}, format="json")
        mine = self.filler_count(self.upload().data["id"])
        other = client_for(make_user("bob"))
        theirs = other.get("/api/v1/recordings/%s/analysis/" % self.upload(other).data["id"]).data
        self.assertLess(theirs["summary"]["filler_count"], mine)
