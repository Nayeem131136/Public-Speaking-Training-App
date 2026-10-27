"""Settings that admins can change, with their starting values."""

DEFAULTS = {
    "max_recording_seconds": 300,
    "min_recording_seconds": 10,
    "wpm_target_min": 120,
    "wpm_target_max": 160,
    "pacing_window_seconds": 30,
    "pause_min_seconds": 0.5,
    "pause_dramatic_min_seconds": 1.0,
    "pause_long_min_seconds": 3.0,
    "whisper_model": "base",
    "default_language": "en",
}

DESCRIPTIONS = {
    "max_recording_seconds": "Longest recording we accept (5 minutes)",
    "min_recording_seconds": "Anything shorter is too little to analyze",
    "wpm_target_min": "Lower end of a good pace (words per minute)",
    "wpm_target_max": "Upper end of a good pace (words per minute)",
    "pacing_window_seconds": "Window size for the pace chart",
    "pause_min_seconds": "Gaps shorter than this are not pauses",
    "pause_dramatic_min_seconds": "From here a pause is called dramatic",
    "pause_long_min_seconds": "From here a pause is called long",
    "whisper_model": "tiny, base, small or medium. Bigger is slower but more accurate",
    "default_language": "Used when the request does not send a language (en or bn)",
}

# Settings that must be one of a few text values.
CHOICES = {
    "whisper_model": ["tiny", "base", "small", "medium"],
    "default_language": ["en", "bn"],
}
