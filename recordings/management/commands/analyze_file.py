"""Test the speech engine on one file: python manage.py analyze_file file.wav"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from appconfig.defaults import DEFAULTS
from appconfig.settings_store import get_all_settings
from appconfig.word_lists import get_active_filler_words
from services.audio import get_audio_duration
from services.errors import ProcessingError
from services.fillers import DEFAULT_FILLER_WORDS, detect_fillers
from services.pauses import detect_pauses
from services.transcription import transcribe
from services.wpm import compute_wpm, pacing_status


class Command(BaseCommand):
    help = "Transcribe one audio file and print the pace, pauses and filler words."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path to the audio file")
        parser.add_argument("--language", default="en", choices=["en", "bn"])
        parser.add_argument("--model", default=None, help="tiny, base, small or medium")
        parser.add_argument("--engine", default=None, choices=["auto", "faster-whisper", "mock"])

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.is_file():
            raise CommandError("File not found: %s" % path)
        language = options["language"]

        try:
            settings = get_all_settings()
            filler_words = get_active_filler_words(None, language)
        except DatabaseError:  # the database was not migrated yet, use the built-in values
            settings = dict(DEFAULTS)
            filler_words = list(DEFAULT_FILLER_WORDS) if language == "en" else []

        duration = get_audio_duration(path)
        try:
            result = transcribe(
                path, language, options["model"] or settings["whisper_model"],
                duration_hint=duration, engine=options["engine"],
            )
        except ProcessingError as error:
            raise CommandError(error.message)

        duration = duration or result.duration or (result.words[-1].end if result.words else 0.0)
        pauses = detect_pauses(
            result.words, settings["pause_min_seconds"],
            settings["pause_dramatic_min_seconds"], settings["pause_long_min_seconds"],
        )
        wpm = compute_wpm(result.words, duration, settings["pacing_window_seconds"], pauses)
        fillers = detect_fillers(result.words, filler_words)

        marked = set()
        for hit in fillers:
            for index, word in enumerate(result.words):
                if word.start >= hit.start - 1e-6 and word.end <= hit.end + 1e-6:
                    marked.add(index)
        text = " ".join("[%s]" % w.word if i in marked else w.word for i, w in enumerate(result.words))

        status = pacing_status(wpm.wpm, settings["wpm_target_min"], settings["wpm_target_max"], wpm.total_words)
        out = self.stdout.write
        out("Engine:   %s" % result.engine)
        out("Length:   %.1f seconds" % duration)
        out("Words:    %s" % wpm.total_words)
        out("Pace:     %s words per minute (%s, target %s-%s)" % (
            wpm.wpm, status, settings["wpm_target_min"], settings["wpm_target_max"]))
        out("Pauses:   %s" % len(pauses))
        for pause in pauses[:10]:
            out("   %6.2fs  %.2fs  %s" % (pause.start, pause.duration, pause.kind))
        out("Fillers:  %s" % len(fillers))
        counts = {}
        for hit in fillers:
            counts[hit.word] = counts.get(hit.word, 0) + 1
        for word, count in sorted(counts.items(), key=lambda item: -item[1]):
            out("   %-12s %s" % (word, count))
        out("")
        out("Transcript (filler words in [brackets]):")
        out(text)
        if result.engine == "mock":
            out("")
            out("NOTE: this is the MOCK engine, not your audio. Whisper is not installed or its model is not downloaded.")
            out("Run: python run.py   (needs internet the first time)")
