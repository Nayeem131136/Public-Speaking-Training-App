from services.breakdown import build_breakdown


def breakdown_for_recording(recording):
    """Load the saved results of a completed recording and build the response."""
    analysis = recording.analysis
    summary = {
        "total_words": analysis.total_words,
        "wpm": analysis.wpm,
        "speaking_seconds": analysis.speaking_seconds,
        "filler_count": analysis.filler_count,
        "pause_count": analysis.pause_count,
        "longest_pause_sec": analysis.longest_pause_sec,
    }
    fillers = [
        {"word": f.word, "start_sec": f.start_sec, "end_sec": f.end_sec} for f in analysis.filler_occurrences.all()
    ]
    pauses = [
        {"start_sec": p.start_sec, "end_sec": p.end_sec, "duration_sec": p.duration_sec, "kind": p.kind}
        for p in analysis.pause_events.all()
    ]
    return build_breakdown(
        recording.id, recording.duration_sec, summary, analysis.pacing_segments, fillers, pauses,
        analysis.settings_snapshot,
    )
