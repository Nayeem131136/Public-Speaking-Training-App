from django.test import SimpleTestCase

from services.types import Pause, Word
from services.wpm import compute_wpm, pacing_status


def words_every(step, count):
    return [Word("w%d" % i, i * step, i * step + 0.2) for i in range(count)]


class ComputeWpmTests(SimpleTestCase):
    def test_overall_wpm(self):
        result = compute_wpm(words_every(0.5, 60), 30)  # 60 words in 30 seconds
        self.assertEqual(result.total_words, 60)
        self.assertEqual(result.wpm, 120.0)

    def test_no_words(self):
        result = compute_wpm([], 30)
        self.assertEqual(result.total_words, 0)
        self.assertEqual(result.wpm, 0.0)
        self.assertTrue(all(s.wpm == 0 for s in result.segments))

    def test_zero_duration_falls_back_to_the_last_word(self):
        words = [Word("a", 0.0, 1.0), Word("b", 1.0, 2.0)]
        self.assertEqual(compute_wpm(words, 0).wpm, 60.0)

    def test_nothing_at_all(self):
        result = compute_wpm([], 0)
        self.assertEqual(result.wpm, 0.0)
        self.assertEqual(result.segments, [])

    def test_windows_of_30_seconds(self):
        result = compute_wpm(words_every(1.0, 90), 90, window_sec=30)
        self.assertEqual([(s.start_sec, s.end_sec) for s in result.segments], [(0, 30), (30, 60), (60, 90)])
        self.assertTrue(all(s.wpm == 60.0 for s in result.segments))

    def test_a_short_last_window_is_merged_into_the_one_before(self):
        result = compute_wpm(words_every(1.0, 70), 70, window_sec=30)
        self.assertEqual([(s.start_sec, s.end_sec) for s in result.segments], [(0, 30), (30, 70)])
        self.assertEqual(result.segments[1].wpm, 60.0)

    def test_a_recording_shorter_than_one_window_has_one_segment(self):
        result = compute_wpm(words_every(1.0, 20), 20, window_sec=30)
        self.assertEqual(len(result.segments), 1)
        self.assertEqual(result.segments[0].end_sec, 20)

    def test_speaking_time_leaves_out_long_pauses_only(self):
        pauses = [Pause(10, 15, 5.0, "long"), Pause(20, 21, 1.0, "dramatic")]
        result = compute_wpm(words_every(1.0, 60), 60, pauses=pauses)
        self.assertEqual(result.speaking_seconds, 55.0)


class PacingStatusTests(SimpleTestCase):
    def test_statuses(self):
        self.assertEqual(pacing_status(100, 120, 160, 50), "too_slow")
        self.assertEqual(pacing_status(120, 120, 160, 50), "within_target")
        self.assertEqual(pacing_status(160, 120, 160, 50), "within_target")
        self.assertEqual(pacing_status(170, 120, 160, 50), "too_fast")

    def test_no_speech(self):
        self.assertEqual(pacing_status(0, 120, 160, 0), "no_speech")
