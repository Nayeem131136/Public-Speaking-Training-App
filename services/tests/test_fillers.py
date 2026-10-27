from django.test import SimpleTestCase

from services.fillers import detect_fillers, normalize
from services.types import Word


def make_words(text, step=0.5):
    return [Word(token, i * step, i * step + 0.3) for i, token in enumerate(text.split())]


class DetectFillersTests(SimpleTestCase):
    def found(self, text, filler_words):
        return [hit.word for hit in detect_fillers(make_words(text), filler_words)]

    def test_single_words(self):
        self.assertEqual(self.found("So um I like pizza uh", ["um", "uh", "like"]), ["um", "like", "uh"])

    def test_case_and_punctuation_do_not_matter(self):
        self.assertEqual(self.found("Um, well... UH. okay", ["um", "uh"]), ["um", "uh"])

    def test_a_phrase_is_matched_as_words_in_a_row(self):
        hits = detect_fillers(make_words("it is, you know, fine"), ["you know"])
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].word, "you know")
        self.assertEqual(hits[0].start, 1.0)  # the start of "you"
        self.assertEqual(hits[0].end, 1.5 + 0.3)  # the end of "know,"

    def test_the_longer_phrase_wins(self):
        self.assertEqual(self.found("well you know it", ["you", "you know"]), ["you know"])

    def test_filler_must_be_the_whole_word(self):
        self.assertEqual(self.found("mum is yum", ["um"]), [])

    def test_empty_list_or_no_words(self):
        self.assertEqual(self.found("um uh", []), [])
        self.assertEqual(detect_fillers([], ["um"]), [])

    def test_list_entries_are_normalized_too(self):
        self.assertEqual(self.found("well um okay", ["  UM. "]), ["um"])

    def test_bangla_filler(self):
        words = [Word("আমি", 0, 0.3), Word("ইয়ে,", 0.5, 0.8), Word("মানে", 1.0, 1.3), Word("যাব", 1.5, 1.8)]
        hits = detect_fillers(words, ["ইয়ে", "মানে"])
        self.assertEqual([h.word for h in hits], ["ইয়ে", "মানে"])

    def test_same_word_twice(self):
        self.assertEqual(self.found("um um um", ["um"]), ["um", "um", "um"])


class NormalizeTests(SimpleTestCase):
    def test_normalize(self):
        self.assertEqual(normalize(" Um, "), "um")
        self.assertEqual(normalize("\u201cHello!\u201d"), "hello")
        self.assertEqual(normalize("don't"), "don't")
        self.assertEqual(normalize("ইয়ে।"), "ইয়ে")
