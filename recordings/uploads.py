"""Check an uploaded audio file and save it to a temporary place."""
import uuid
from pathlib import Path

from django.conf import settings

from config.exceptions import ApiError
from services.audio import get_audio_duration


def check_and_save_upload(uploaded, min_seconds, max_seconds):
    """Check the uploaded file and save it in the temp folder."""
    extension = Path(uploaded.name).suffix.lower()
    allowed = settings.ALLOWED_AUDIO_EXTENSIONS
    if extension not in allowed:
        raise ApiError(415, "unsupported_format", "Use one of these formats: %s." % ", ".join(allowed))
    if uploaded.size == 0:
        raise ApiError(400, "validation_error", "The audio file is empty.")
    if uploaded.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise ApiError(413, "file_too_large", "The file is larger than %s MB." % settings.MAX_UPLOAD_MB)

    folder = Path(settings.TEMP_AUDIO_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (uuid.uuid4().hex + extension)
    with open(path, "wb") as target:
        for chunk in uploaded.chunks():
            target.write(chunk)

    duration = get_audio_duration(path)
    if duration is not None:
        if duration < min_seconds:
            path.unlink(missing_ok=True)
            raise ApiError(400, "audio_too_short", "The recording is too short. Minimum is %s seconds." % min_seconds)
        if duration > max_seconds:
            path.unlink(missing_ok=True)
            raise ApiError(400, "audio_too_long", "The recording is too long. Maximum is %s seconds." % max_seconds)
    return path, duration
