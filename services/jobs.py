"""Start the processing of a recording without making the user wait."""
import threading

from django.conf import settings
from django.db import connections

from .pipeline import process_recording


def start_processing(recording_id, audio_path):
    """Run in a background thread, or right away when PROCESS_SYNC is on."""
    if settings.PROCESS_SYNC:
        process_recording(recording_id, audio_path)
        return
    thread = threading.Thread(target=_run, args=(recording_id, audio_path), daemon=True)
    thread.start()


def _run(recording_id, audio_path):
    try:
        process_recording(recording_id, audio_path)
    finally:
        connections.close_all()  # a thread has its own database connection
