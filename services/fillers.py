"""Find filler words such as "um" or "you know" in the timed words."""
import string

from .types import FillerHit

# Used when the database has no filler words yet.
DEFAULT_FILLER_WORDS = [
    "um", "uh", "er", "ah", "like", "you know", "so", "actually", "basically", "i mean", "right",
]

# punctuation to strip from the ends, includes the Bangla danda
_PUNCTUATION = string.punctuation + "\u201c\u201d\u2018\u2019\u2026\u2013\u2014\u0964"


def normalize(text):
    """'Um,' -> 'um'.  Only the ends are stripped, so "don't" stays as it is."""
    return text.strip().strip(_PUNCTUATION).strip().lower()


def detect_fillers(words, filler_words):
    """Find filler words and phrases in the list of timed words."""
    phrases = set()
    for item in filler_words:
        parts = tuple(p for p in (normalize(x) for x in item.split()) if p)
        if parts:
            phrases.add(parts)
    phrases = sorted(phrases, key=len, reverse=True)

    tokens = [normalize(w.word) for w in words]
    hits = []
    i = 0
    while i < len(words):
        for phrase in phrases:
            size = len(phrase)
            if tuple(tokens[i:i + size]) == phrase:
                hits.append(FillerHit(" ".join(phrase), words[i].start, words[i + size - 1].end))
                i += size
                break
        else:
            i += 1
    return hits
