"""Build the JSON that the performance breakdown screen needs."""
from .wpm import pacing_status


def build_breakdown(recording_id, duration_sec, summary, segments, fillers, pauses, settings):
    """Make the json for the breakdown screen from the saved results."""
    target_min = settings["wpm_target_min"]
    target_max = settings["wpm_target_max"]

    counts = {}
    for filler in fillers:
        counts[filler["word"]] = counts.get(filler["word"], 0) + 1
    by_word = dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))

    return {
        "recording_id": recording_id,
        "status": "completed",
        "duration_sec": duration_sec,
        "summary": summary,
        "pacing": {
            "target_min": target_min,
            "target_max": target_max,
            "status": pacing_status(summary["wpm"], target_min, target_max, summary["total_words"]),
            "segments": segments,
        },
        "fillers": {"by_word": by_word, "occurrences": fillers},
        "pauses": pauses,
    }
