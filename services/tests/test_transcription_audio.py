import os
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from config.testing import make_wav
from services.audio import get_audio_duration
from services.errors import TranscriptionError
from services import transcription
from services.transcription import _collect_words, transcribe


class MockTranscriptionTests(SimpleTestCase):
    def test_mock_fills_the_recording_length(self):
        result = transcribe("any.wav", "en", duration_hint=30, engine="mock")
        self.assertEqual(result.engine, "mock")
        self.assertGreater(len(result.words), 20)
        self.assertLessEqual(result.words[-1].end, 30)
        self.assertEqual(result.duration, 30)

    def test_mock_words_are_in_time_order(self):
        words = transcribe("any.wav", "en", duration_hint=60, engine="mock").words
        for earlier, later in zip(words, words[1:]):
            self.assertLessEqual(earlier.end, later.start)

    def test_mock_without_length_does_one_pass(self):
        result = transcribe("any.wav", "en", engine="mock")
        self.assertGreater(len(result.words), 0)

    def test_unknown_engine_is_an_error(self):
        with self.assertRaises(TranscriptionError):
            transcribe("any.wav", "en", engine="nope")


class AutoEngineTests(SimpleTestCase):
    def setUp(self):
        transcription._model_failed.clear()
        no_problem = patch("services.transcription.decoder_problem", return_value=None)
        no_problem.start()
        self.addCleanup(no_problem.stop)

    @override_settings(TRANSCRIBER="auto")
    def test_falls_back_to_mock_when_the_model_cannot_load(self):
        fake_module = SimpleNamespace()
        with patch.dict(sys.modules, {"faster_whisper": fake_module}):
            with patch("services.transcription._get_model", side_effect=OSError("no internet")):
                with self.assertLogs("services.transcription", level="WARNING"):
                    result = transcribe("any.wav", "en", duration_hint=20)
        self.assertEqual(result.engine, "mock")

    @override_settings(TRANSCRIBER="auto")
    def test_does_not_try_again_right_after_a_failure(self):
        fake_module = SimpleNamespace()
        with patch.dict(sys.modules, {"faster_whisper": fake_module}):
            with patch("services.transcription._get_model", side_effect=OSError("no internet")) as loader:
                with self.assertLogs("services.transcription", level="WARNING"):
                    transcribe("any.wav", "en", duration_hint=20)
                transcribe("any.wav", "en", duration_hint=20)
        self.assertEqual(loader.call_count, 1)

    def test_strict_mode_does_not_fall_back(self):
        with patch("services.transcription._get_model", side_effect=OSError("no internet")):
            with self.assertRaises(TranscriptionError):
                transcribe("any.wav", "en", engine="faster-whisper")


class WhisperProblemTests(SimpleTestCase):
    def setUp(self):
        transcription._model_failed.clear()
        transcription._decoder.update(checked=False, problem=None)
        self.addCleanup(transcription._decoder.update, checked=False, problem=None)

    @override_settings(TRANSCRIBER="auto")
    def test_broken_audio_decoder_means_mock_instead_of_failed_uploads(self):
        with patch.dict(sys.modules, {"faster_whisper": SimpleNamespace()}):
            with patch("services.transcription.decoder_problem", return_value="TypeError: boom"):
                with self.assertLogs("services.transcription", level="WARNING") as logs:
                    result = transcribe("any.wav", "en", duration_hint=20)
        self.assertEqual(result.engine, "mock")
        self.assertIn("av<19", logs.output[0])

    def test_the_real_reason_is_in_the_error_message(self):
        model = SimpleNamespace(transcribe=lambda *a, **k: (_ for _ in ()).throw(ValueError("bad audio")))
        with patch("services.transcription._get_model", return_value=model):
            with self.assertLogs("services.transcription", level="ERROR"):
                with self.assertRaises(TranscriptionError) as caught:
                    transcribe("any.wav", "en", engine="faster-whisper")
        self.assertIn("ValueError: bad audio", caught.exception.message)
        self.assertLessEqual(len(caught.exception.message), 255)  # fits the database field


class WhisperResultTests(SimpleTestCase):
    def test_collect_words_flattens_segments_and_skips_empty_words(self):
        segments = [
            SimpleNamespace(words=[
                SimpleNamespace(word=" Um,", start=0.1, end=0.4),
                SimpleNamespace(word="  ", start=0.4, end=0.5),
                SimpleNamespace(word=" hello", start=0.6, end=1.0),
            ]),
            SimpleNamespace(words=None),
            SimpleNamespace(words=[SimpleNamespace(word=" there", start=1.2, end=1.5)]),
        ]
        words = _collect_words(segments)
        self.assertEqual([w.word for w in words], ["Um,", "hello", "there"])
        self.assertEqual(words[2].start, 1.2)


class AudioDurationTests(SimpleTestCase):
    def test_wav_length(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "a.wav")
            with open(path, "wb") as f:
                f.write(make_wav(12.5).read())
            self.assertAlmostEqual(get_audio_duration(path), 12.5, places=2)

    def test_unreadable_file_gives_none(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "a.mp3")
            with open(path, "wb") as f:
                f.write(b"not audio")
            self.assertIsNone(get_audio_duration(path))

    def test_missing_file_gives_none(self):
        self.assertIsNone(get_audio_duration("/no/such/file.wav"))
