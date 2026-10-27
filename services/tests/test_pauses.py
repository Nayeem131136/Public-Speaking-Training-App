from django.test import SimpleTestCase

from services.pauses import detect_pauses, pause_kind
from services.types import Word


class DetectPausesTests(SimpleTestCase):
    def test_small_gaps_are_ignored_and_the_rest_are_labeled(self):
        words = [Word("a", 0, 1), Word("b", 1.3, 2), Word("c", 3.2, 4), Word("d", 8, 9)]
        pauses = detect_pauses(words)
        self.assertEqual([p.kind for p in pauses], ["dramatic", "long"])
        self.assertEqual((pauses[0].start, pauses[0].end, pauses[0].duration), (2, 3.2, 1.2))

    def test_the_limits_belong_to_the_bigger_label(self):
        words = [Word("a", 0, 1), Word("b", 1.5, 2), Word("c", 3.0, 4), Word("d", 7.0, 8)]
        self.assertEqual([p.kind for p in detect_pauses(words)], ["short", "dramatic", "long"])

    def test_no_pauses(self):
        self.assertEqual(detect_pauses([Word("a", 0, 1), Word("b", 1.1, 2)]), [])

    def test_one_word_or_none(self):
        self.assertEqual(detect_pauses([Word("a", 0, 1)]), [])
        self.assertEqual(detect_pauses([]), [])

    def test_custom_limits(self):
        words = [Word("a", 0, 1), Word("b", 1.3, 2)]
        self.assertEqual(len(detect_pauses(words, min_seconds=0.2)), 1)
        self.assertEqual(detect_pauses(words, min_seconds=0.4), [])

    def test_pause_kind(self):
        self.assertEqual(pause_kind(0.6), "short")
        self.assertEqual(pause_kind(2.0), "dramatic")
        self.assertEqual(pause_kind(5.0), "long")
