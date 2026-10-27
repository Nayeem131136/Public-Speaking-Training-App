from django.test import SimpleTestCase

from services.breakdown import build_breakdown

SUMMARY = {
    "total_words": 100, "wpm": 140.0, "speaking_seconds": 40.0,
    "filler_count": 3, "pause_count": 1, "longest_pause_sec": 1.5,
}
FILLERS = [
    {"word": "um", "start_sec": 3.0, "end_sec": 3.2},
    {"word": "like", "start_sec": 5.0, "end_sec": 5.3},
    {"word": "um", "start_sec": 9.0, "end_sec": 9.2},
]
PAUSES = [{"start_sec": 10.0, "end_sec": 11.5, "duration_sec": 1.5, "kind": "dramatic"}]
SEGMENTS = [{"start_sec": 0, "end_sec": 42.5, "wpm": 140.0}]
SETTINGS = {"wpm_target_min": 120, "wpm_target_max": 160}


class BuildBreakdownTests(SimpleTestCase):
    def build(self, **changes):
        summary = dict(SUMMARY, **changes)
        return build_breakdown(7, 42.5, summary, SEGMENTS, FILLERS, PAUSES, SETTINGS)

    def test_shape(self):
        data = self.build()
        self.assertEqual(data["recording_id"], 7)
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["duration_sec"], 42.5)
        self.assertEqual(data["summary"], SUMMARY)
        self.assertEqual(data["pauses"], PAUSES)
        self.assertEqual(data["pacing"]["segments"], SEGMENTS)
        self.assertEqual((data["pacing"]["target_min"], data["pacing"]["target_max"]), (120, 160))

    def test_fillers_are_counted_by_word_most_used_first(self):
        data = self.build()
        self.assertEqual(data["fillers"]["by_word"], {"um": 2, "like": 1})
        self.assertEqual(list(data["fillers"]["by_word"]), ["um", "like"])
        self.assertEqual(len(data["fillers"]["occurrences"]), 3)

    def test_pacing_status(self):
        self.assertEqual(self.build()["pacing"]["status"], "within_target")
        self.assertEqual(self.build(wpm=200.0)["pacing"]["status"], "too_fast")
        self.assertEqual(self.build(wpm=80.0)["pacing"]["status"], "too_slow")
        self.assertEqual(self.build(wpm=0.0, total_words=0)["pacing"]["status"], "no_speech")

    def test_no_fillers(self):
        data = build_breakdown(1, 20, SUMMARY, SEGMENTS, [], [], SETTINGS)
        self.assertEqual(data["fillers"], {"by_word": {}, "occurrences": []})
