"""Find the pauses between words."""
from .types import Pause


def pause_kind(duration, dramatic_min=1.0, long_min=3.0):
    if duration >= long_min:
        return "long"
    if duration >= dramatic_min:
        return "dramatic"
    return "short"


def detect_pauses(words, min_seconds=0.5, dramatic_min=1.0, long_min=3.0):
    """A pause is a gap between two words that is at least min_seconds long."""
    pauses = []
    for previous, following in zip(words, words[1:]):
        gap = round(following.start - previous.end, 2)
        if gap >= min_seconds:
            pauses.append(
                Pause(
                    start=round(previous.end, 2),
                    end=round(following.start, 2),
                    duration=gap,
                    kind=pause_kind(gap, dramatic_min, long_min),
                )
            )
    return pauses
