from config.testing import ApiTestCase, make_user, client_for
from prompts.models import Category, Prompt
from recordings.models import Recording


class RecordingApiTests(ApiTestCase):
    def test_needs_login(self):
        self.assertEqual(self.client.get("/api/v1/recordings/").status_code, 401)

    def test_upload_returns_202_and_the_recording_completes(self):
        response = self.upload()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], "processing")

        detail = self.api.get("/api/v1/recordings/%s/" % response.data["id"])
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["status"], "completed")
        self.assertGreater(detail.data["summary"]["total_words"], 0)
        self.assertAlmostEqual(detail.data["duration_sec"], 15.0, places=1)

    def test_transcript(self):
        recording_id = self.upload().data["id"]
        response = self.api.get("/api/v1/recordings/%s/transcript/" % recording_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["engine"], "mock")
        self.assertTrue(response.data["full_text"])
        self.assertEqual(set(response.data["words"][0]), {"word", "start", "end"})

    def test_analysis_has_everything_the_breakdown_screen_needs(self):
        recording_id = self.upload().data["id"]
        data = self.api.get("/api/v1/recordings/%s/analysis/" % recording_id).data
        self.assertEqual(data["recording_id"], recording_id)
        self.assertEqual(data["status"], "completed")
        self.assertEqual(
            set(data["summary"]),
            {"total_words", "wpm", "speaking_seconds", "filler_count", "pause_count", "longest_pause_sec"},
        )
        self.assertIn(data["pacing"]["status"], ["too_slow", "within_target", "too_fast"])
        self.assertEqual(data["pacing"]["target_min"], 120)
        self.assertGreaterEqual(len(data["pacing"]["segments"]), 1)
        self.assertEqual(data["fillers"]["by_word"] and sum(data["fillers"]["by_word"].values()),
                         data["summary"]["filler_count"])
        self.assertEqual(len(data["pauses"]), data["summary"]["pause_count"])

    def test_list_shows_only_my_recordings(self):
        mine = self.upload().data["id"]
        other_client = client_for(make_user("bob"))
        self.upload(other_client)
        response = self.api.get("/api/v1/recordings/")
        self.assertEqual([r["id"] for r in response.data["results"]], [mine])

    def test_someone_elses_recording_is_not_found(self):
        recording_id = self.upload().data["id"]
        other_client = client_for(make_user("bob"))
        for suffix in ["", "transcript/", "analysis/"]:
            response = other_client.get("/api/v1/recordings/%s/%s" % (recording_id, suffix))
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.data["error"]["code"], "not_found")
        self.assertEqual(other_client.delete("/api/v1/recordings/%s/" % recording_id).status_code, 404)

    def test_delete_removes_the_recording_and_its_results(self):
        recording_id = self.upload().data["id"]
        self.assertEqual(self.api.delete("/api/v1/recordings/%s/" % recording_id).status_code, 204)
        self.assertEqual(self.api.get("/api/v1/recordings/%s/" % recording_id).status_code, 404)
        self.assertFalse(Recording.objects.filter(id=recording_id).exists())

    def test_upload_with_prompt(self):
        prompt = Prompt.objects.create(category=Category.objects.create(name="Talk"), title="t", text="t")
        recording_id = self.upload(prompt_id=prompt.id).data["id"]
        self.assertEqual(Recording.objects.get(id=recording_id).prompt_id, prompt.id)
        response = self.api.get("/api/v1/recordings/?prompt_id=%s" % prompt.id)
        self.assertEqual(response.data["count"], 1)

    def test_upload_with_unknown_prompt_fails(self):
        response = self.upload(prompt_id=9999)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")

    def test_bad_prompt_id_filter_fails(self):
        response = self.api.get("/api/v1/recordings/?prompt_id=abc")
        self.assertEqual(response.status_code, 400)

    def test_language_is_saved(self):
        recording_id = self.upload(language="bn").data["id"]
        self.assertEqual(Recording.objects.get(id=recording_id).language, "bn")

    def test_unknown_language_fails(self):
        self.assertEqual(self.upload(language="fr").status_code, 400)

    def test_analysis_while_processing_says_not_ready(self):
        recording = Recording.objects.create(user=self.user, status=Recording.PROCESSING)
        for suffix in ["transcript/", "analysis/"]:
            response = self.api.get("/api/v1/recordings/%s/%s" % (recording.id, suffix))
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.data["error"]["code"], "not_ready")

    def test_failed_recording_shows_the_error(self):
        recording = Recording.objects.create(
            user=self.user, status=Recording.FAILED, error_code="transcription_failed", error_message="Nope"
        )
        detail = self.api.get("/api/v1/recordings/%s/" % recording.id)
        self.assertEqual(detail.data["error"], {"code": "transcription_failed", "message": "Nope"})
        response = self.api.get("/api/v1/recordings/%s/analysis/" % recording.id)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["error"]["code"], "recording_failed")

    def test_wrong_http_method_gets_our_error_format(self):
        response = self.api.put("/api/v1/recordings/")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.data["error"]["code"], "method_not_allowed")
