"""Steps for one recording: transcribe, pauses, pace, fillers, save."""
import logging
import os

from django.db import transaction
from django.utils import timezone

from analysis.models import AnalysisResult, FillerOccurrence, PauseEvent
from appconfig.settings_store import get_all_settings
from appconfig.word_lists import get_active_filler_words
from recordings.models import Recording, Transcript

from .errors import ProcessingError
from .fillers import detect_fillers
from .pauses import detect_pauses
from .transcription import transcribe
from .wpm import compute_wpm

logger = logging.getLogger(__name__)


def process_recording(recording_id, audio_path):
    """Process one recording. Marks it failed on any error, always deletes the audio."""
    try:
        recording = Recording.objects.select_related("user").get(id=recording_id)
    except Recording.DoesNotExist:
        _delete_file(audio_path)
        return

    try:
        _run(recording, audio_path)
    except ProcessingError as error:
        _mark_failed(recording, error.code, error.message)
    except Exception:
        logger.exception("Processing failed for recording %s", recording_id)
        _mark_failed(recording, "processing_failed", "Something went wrong while processing the audio.")
    finally:
        _delete_file(audio_path)


def _run(recording, audio_path):
    settings = get_all_settings()

    result = transcribe(
        audio_path,
        recording.language,
        settings["whisper_model"],
        duration_hint=recording.duration_sec,
    )

    duration = recording.duration_sec or result.duration or (result.words[-1].end if result.words else 0.0)
    # the length is not always known at upload (webm), so check again here
    if duration < settings["min_recording_seconds"]:
        raise ProcessingError("audio_too_short", "The recording is too short to analyze.")
    if duration > settings["max_recording_seconds"]:
        raise ProcessingError("audio_too_long", "The recording is longer than the allowed time.")

    pauses = detect_pauses(
        result.words,
        settings["pause_min_seconds"],
        settings["pause_dramatic_min_seconds"],
        settings["pause_long_min_seconds"],
    )
    wpm = compute_wpm(result.words, duration, settings["pacing_window_seconds"], pauses)
    filler_words = get_active_filler_words(recording.user, recording.language)
    fillers = detect_fillers(result.words, filler_words)

    with transaction.atomic():
        Transcript.objects.update_or_create(
            recording=recording,
            defaults={
                "full_text": result.text,
                "words": [{"word": w.word, "start": w.start, "end": w.end} for w in result.words],
                "engine": result.engine,
            },
        )
        analysis = AnalysisResult.objects.create(
            recording=recording,
            total_words=wpm.total_words,
            speaking_seconds=wpm.speaking_seconds,
            wpm=wpm.wpm,
            filler_count=len(fillers),
            pause_count=len(pauses),
            longest_pause_sec=max((p.duration for p in pauses), default=0.0),
            pacing_segments=[
                {"start_sec": s.start_sec, "end_sec": s.end_sec, "wpm": s.wpm} for s in wpm.segments
            ],
            settings_snapshot=settings,
        )
        FillerOccurrence.objects.bulk_create(
            [FillerOccurrence(analysis=analysis, word=f.word, start_sec=f.start, end_sec=f.end) for f in fillers]
        )
        PauseEvent.objects.bulk_create(
            [
                PauseEvent(analysis=analysis, start_sec=p.start, end_sec=p.end, duration_sec=p.duration, kind=p.kind)
                for p in pauses
            ]
        )
        recording.status = Recording.COMPLETED
        recording.duration_sec = round(duration, 2)
        recording.completed_at = timezone.now()
        recording.error_code = ""
        recording.error_message = ""
        recording.save()


def _mark_failed(recording, code, message):
    recording.status = Recording.FAILED
    recording.error_code = code
    recording.error_message = message
    recording.completed_at = timezone.now()
    recording.save(update_fields=["status", "error_code", "error_message", "completed_at"])


def _delete_file(path):
    try:
        os.remove(path)
    except OSError:
        pass
