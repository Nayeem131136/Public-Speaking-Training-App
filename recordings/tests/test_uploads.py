import os
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from appconfig.models import AppSetting
from config.testing import ApiTestCase
from recordings.models import Recording
from services.errors import TranscriptionError
from services.types import TranscriptResult


class UploadCheckTests(ApiTestCase):
    def temp_files(self):
        return os.listdir(self.tmp.name)

    def test_too_short(self):
        response = self.upload(seconds=3)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "audio_too_short")
        self.assertEqual(self.temp_files(), [])
        self.assertEqual(Recording.objects.count(), 0)

    def test_too_long_uses_the_admin_setting(self):
        AppSetting.objects.create(key="max_recording_seconds", value=20)
        response = self.upload(seconds=30)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "audio_too_long")
        self.assertEqual(self.temp_files(), [])

    def test_unsupported_format(self):
        bad = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
        response = self.api.post("/api/v1/recordings/", {"audio": bad}, format="multipart")
        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.data["error"]["code"], "unsupported_format")

    @override_settings(MAX_UPLOAD_MB=0.01)
    def test_file_too_large(self):
        response = self.upload(seconds=15)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.data["error"]["code"], "file_too_large")

    def test_empty_file(self):
        empty = SimpleUploadedFile("empty.wav", b"", content_type="audio/wav")
        response = self.api.post("/api/v1/recordings/", {"audio": empty}, format="multipart")
        self.assertEqual(response.status_code, 400)

    def test_missing_audio_field(self):
        response = self.api.post("/api/v1/recordings/", {}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("audio", response.data["error"]["fields"])

    def test_other_formats_are_accepted_when_the_length_is_unknown(self):
        # length of a fake webm is unknown, so it is checked later in the pipeline
        fake = SimpleUploadedFile("take.webm", b"not really audio", content_type="audio/webm")
        response = self.api.post("/api/v1/recordings/", {"audio": fake}, format="multipart")
        self.assertEqual(response.status_code, 202)


class InterruptedAndHugeTests(ApiTestCase):
    def test_recording_stuck_in_processing_is_marked_failed(self):
        from datetime import timedelta

        from django.utils import timezone

        stuck = Recording.objects.create(user=self.user, status=Recording.PROCESSING)
        recent = Recording.objects.create(user=self.user, status=Recording.PROCESSING)
        Recording.objects.filter(id=stuck.id).update(created_at=timezone.now() - timedelta(minutes=30))

        data = self.api.get("/api/v1/recordings/%s/" % stuck.id).data
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["error"]["code"], "interrupted")
        self.assertEqual(self.api.get("/api/v1/recordings/%s/" % recent.id).data["status"], "processing")

    def test_a_huge_upload_is_refused_before_it_is_read(self):
        response = self.api.post("/api/v1/recordings/", {}, format="multipart", CONTENT_LENGTH=str(500 * 1024 * 1024))
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.data["error"]["code"], "file_too_large")


class AudioIsAlwaysDeletedTests(ApiTestCase):
    def test_deleted_after_success(self):
        self.upload()
        self.assertEqual(os.listdir(self.tmp.name), [])

    def test_deleted_after_failure_and_recording_is_marked_failed(self):
        with patch("services.pipeline.transcribe", side_effect=TranscriptionError()):
            response = self.upload()
        self.assertEqual(response.status_code, 202)
        recording = Recording.objects.get(id=response.data["id"])
        self.assertEqual(recording.status, "failed")
        self.assertEqual(recording.error_code, "transcription_failed")
        self.assertEqual(os.listdir(self.tmp.name), [])

    def test_unexpected_crash_is_also_handled(self):
        with patch("services.pipeline.transcribe", side_effect=RuntimeError("boom")):
            with self.assertLogs("services.pipeline", level="ERROR"):
                response = self.upload()
        recording = Recording.objects.get(id=response.data["id"])
        self.assertEqual(recording.status, "failed")
        self.assertEqual(recording.error_code, "processing_failed")
        self.assertEqual(os.listdir(self.tmp.name), [])

    def test_length_is_checked_again_when_it_was_unknown_at_upload(self):
        # fake webm has no known length, the engine says 5 seconds which is too short
        short = TranscriptResult(text="", words=[], duration=5.0, engine="mock")
        fake = SimpleUploadedFile("take.webm", b"x" * 100, content_type="audio/webm")
        with patch("services.pipeline.transcribe", return_value=short):
            response = self.api.post("/api/v1/recordings/", {"audio": fake}, format="multipart")
        recording = Recording.objects.get(id=response.data["id"])
        self.assertEqual(recording.status, "failed")
        self.assertEqual(recording.error_code, "audio_too_short")
        self.assertEqual(os.listdir(self.tmp.name), [])
