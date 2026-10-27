"""Helpers shared by the tests."""
import io
import tempfile
import wave

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient


def make_wav(seconds, name="speech.wav"):
    """A silent .wav file of the given length, ready to upload."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\x00\x00" * int(8000 * seconds))
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="audio/wav")


def make_user(username="alice", staff=False, password="StrongPass123"):
    return get_user_model().objects.create_user(username=username, password=password, is_staff=staff)


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class ApiTestCase(TestCase):
    """Base class for API tests. Uses the mock transcriber and a temp folder."""

    def setUp(self):
        cache.clear()  # the upload rate limit is stored in the cache
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        override = override_settings(PROCESS_SYNC=True, TRANSCRIBER="mock", TEMP_AUDIO_DIR=self.tmp.name)
        override.enable()
        self.addCleanup(override.disable)
        self.user = make_user("alice")
        self.api = client_for(self.user)

    def upload(self, client=None, seconds=15, **extra):
        data = {"audio": make_wav(seconds)}
        data.update(extra)
        return (client or self.api).post("/api/v1/recordings/", data, format="multipart")
