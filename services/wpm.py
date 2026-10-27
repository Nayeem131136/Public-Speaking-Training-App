"""Words per minute, and the pace over time."""
from .types import WpmResult, WpmSegment


def compute_wpm(words, duration_sec, window_sec=30, pauses=None):
    """Overall words per minute and the pace for each time window."""
    total_words = len(words)
    duration = duration_sec if duration_sec and duration_sec > 0 else (words[-1].end if words else 0.0)

    wpm = total_words / (duration / 60.0) if duration > 0 else 0.0
    long_pause_time = sum(p.duration for p in (pauses or []) if p.kind == "long")
    speaking_seconds = max(duration - long_pause_time, 0.0)

    return WpmResult(
        total_words=total_words,
        wpm=round(wpm, 1),
        speaking_seconds=round(speaking_seconds, 1),
        segments=_segments(words, duration, window_sec),
    )


def _segments(words, duration, window_sec):
    if duration <= 0 or window_sec <= 0:
        return []

    # start time of each window
    starts = []
    start = 0.0
    while start < duration:
        starts.append(start)
        start += window_sec

    # a very short last window gives a silly pace, so join it to the one before
    if len(starts) > 1 and duration - starts[-1] < window_sec / 2:
        starts.pop()

    segments = []
    for index, seg_start in enumerate(starts):
        is_last = index == len(starts) - 1
        seg_end = duration if is_last else seg_start + window_sec
        if is_last:
            count = sum(1 for w in words if seg_start <= w.start <= seg_end)
        else:
            count = sum(1 for w in words if seg_start <= w.start < seg_end)
        length = seg_end - seg_start
        segments.append(WpmSegment(round(seg_start, 1), round(seg_end, 1), round(count / (length / 60.0), 1)))
    return segments


def pacing_status(wpm, target_min, target_max, total_words=1):
    """'no_speech', 'too_slow', 'too_fast' or 'within_target'."""
    if total_words == 0:
        return "no_speech"
    if wpm < target_min:
        return "too_slow"
    if wpm > target_max:
        return "too_fast"
    return "within_target"
