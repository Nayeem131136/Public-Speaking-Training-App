"""Download and load the Whisper model once: python manage.py prepare_whisper"""
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from appconfig.defaults import DEFAULTS
from appconfig.settings_store import get_all_settings


class Command(BaseCommand):
    help = "Download the Whisper model so the first recording is not slow."

    def add_arguments(self, parser):
        parser.add_argument("--model", default=None, help="tiny, base, small or medium")

    def handle(self, *args, **options):
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            raise CommandError("faster-whisper is not installed. Run: pip install -r requirements-whisper.txt")

        try:
            default_model = get_all_settings()["whisper_model"]
        except DatabaseError:
            default_model = DEFAULTS["whisper_model"]
        model = options["model"] or default_model

        from services.transcription import _get_model, decoder_problem

        problem = decoder_problem()
        if problem:
            raise CommandError(
                "Whisper can't read audio files with the installed packages (%s).\n"
                "Fix: pip install \"av<19\"   (or run: python run.py)" % problem
            )

        self.stdout.write("Loading the '%s' model. The first time this downloads it (needs internet)..." % model)
        try:
            _get_model(model)
        except Exception as exc:
            raise CommandError("Could not load the model: %s" % exc)
        self.stdout.write(self.style.SUCCESS("Whisper is ready."))
