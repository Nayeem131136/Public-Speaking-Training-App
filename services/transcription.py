"""Speech to text. The real engine is faster-whisper, there is also a mock for testing."""
import io
import logging
import os
import threading
import time
import wave

from django.conf import settings

from .errors import TranscriptionError
from .types import TranscriptResult, Word

logger = logging.getLogger(__name__)

# Whisper cleans up speech. A prompt with fillers helps it keep "um" and "uh"
FILLER_PROMPT = "Umm, let me think like, hmm... Okay, so, uh, here's what I'm, like, thinking."

SAMPLE_SPEECH = (
    "So, um, today I want to talk about why practice matters. "
    "You know, most people never rehearse out loud. "
    "Uh, they just read their slides in their head. "
    "And then, like, they are surprised when the real talk feels shaky. "
    "Basically, saying it out loud is a different skill. "
    "I mean, your mouth needs the practice as much as your mind. "
    "Right, so let us try one short run and listen back."
).split()


def transcribe(audio_path, language="en", model_size="base", duration_hint=None, engine=None):
    """Turn an audio file into timed words. Raises TranscriptionError on failure."""
    engine = engine or getattr(settings, "TRANSCRIBER", "auto")

    if engine == "auto":
        engine = _auto_engine(model_size)

    if engine == "mock":
        return _mock_transcribe(duration_hint)
    if engine == "faster-whisper":
        return _whisper_transcribe(audio_path, language, model_size)
    raise TranscriptionError("Unknown TRANSCRIBER setting: %s" % engine)


_models = {}
_models_lock = threading.Lock()
_transcribe_lock = threading.Lock()  # one transcription at a time, laptops are slow
_model_failed = {}  # model size -> when loading it last failed


def _get_model(size):
    """Load the model once and keep it, because loading is slow."""
    with _models_lock:
        if size not in _models:
            from faster_whisper import WhisperModel

            device = os.environ.get("WHISPER_DEVICE", "cpu")
            compute_type = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
            _models[size] = WhisperModel(size, device=device, compute_type=compute_type)
        return _models[size]


_decoder = {"checked": False, "problem": None}


def decoder_problem():
    """None if faster-whisper can read audio files, otherwise a text that says what is wrong."""
    if not _decoder["checked"]:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"\x00\x00" * 16000)
        buffer.seek(0)
        try:
            from faster_whisper.audio import decode_audio

            decode_audio(buffer, sampling_rate=16000)
        except Exception as exc:
            _decoder["problem"] = "%s: %s" % (type(exc).__name__, str(exc)[:120])
        _decoder["checked"] = True
    return _decoder["problem"]


def _auto_engine(model_size):
    """Whisper if it is installed and the model loads, otherwise the mock."""
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        logger.warning("faster-whisper is not installed, using the MOCK transcriber.")
        return "mock"

    problem = decoder_problem()
    if problem:
        logger.warning("Whisper can't read audio (%s). Fix: pip install \"av<19\". Using the MOCK transcriber.", problem)
        return "mock"

    failed_at = _model_failed.get(model_size)
    if failed_at and time.time() - failed_at < 60:  # don't retry on every upload
        return "mock"
    try:
        _get_model(model_size)
    except Exception as exc:
        _model_failed[model_size] = time.time()
        logger.warning("Whisper model '%s' can't be loaded (%s). Using the MOCK transcriber.", model_size, exc)
        return "mock"
    return "faster-whisper"


def _collect_words(segments):
    """Flatten Whisper's segments into one list of Word."""
    words = []
    for segment in segments:
        for item in segment.words or []:
            text = item.word.strip()
            if text:
                words.append(Word(text, float(item.start), float(item.end)))
    return words


def _whisper_transcribe(audio_path, language, model_size):
    try:
        model = _get_model(model_size)
        prompt = os.environ.get("WHISPER_INITIAL_PROMPT", FILLER_PROMPT if language == "en" else None)
        with _transcribe_lock:
            segments, info = model.transcribe(
                str(audio_path), language=language, word_timestamps=True, initial_prompt=prompt
            )
            words = _collect_words(segments)  # segments is lazy, the real work happens here
    except Exception as exc:
        logger.exception("Whisper failed")
        reason = "%s: %s" % (type(exc).__name__, str(exc)[:150])
        raise TranscriptionError("Could not transcribe the audio (%s)." % reason) from exc

    return TranscriptResult(
        text=" ".join(w.word for w in words),
        words=words,
        duration=float(info.duration) if getattr(info, "duration", None) else None,
        engine="faster-whisper",
    )


def _mock_transcribe(duration_hint):
    """Fake speech for testing, around 130 words per minute."""
    words = []
    t = 0.0
    index = 0
    while True:
        token = SAMPLE_SPEECH[index % len(SAMPLE_SPEECH)]
        clean = token.strip(",.")
        length = 0.09 + 0.03 * len(clean)
        if duration_hint and t + length > duration_hint:
            break
        words.append(Word(token, round(t, 2), round(t + length, 2)))
        t += length + 0.06
        if token.endswith(","):
            t += 0.5
        elif token.endswith("."):
            t += 1.1
        index += 1
        if not duration_hint and index >= len(SAMPLE_SPEECH):
            break
    return TranscriptResult(
        text=" ".join(w.word for w in words),
        words=words,
        duration=duration_hint or (words[-1].end if words else 0.0),
        engine="mock",
    )
