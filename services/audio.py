"""Find out how long an audio file is."""
import wave
from pathlib import Path


def get_audio_duration(path):
    """Length of the audio in seconds, or None if we can't read it."""
    path = Path(path)

    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as wav:
                return wav.getnframes() / float(wav.getframerate())
        except (wave.Error, EOFError, OSError, ZeroDivisionError):
            pass

    try:
        import av
    except ImportError:
        return None

    try:
        with av.open(str(path)) as container:
            if container.duration:
                return container.duration / av.time_base
    except Exception:
        return None
    return None
