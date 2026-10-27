from datetime import timedelta

from django.conf import settings as django_settings
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.fields import DateTimeField
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from analysis.utils import breakdown_for_recording
from appconfig.settings_store import get_all_settings
from config.exceptions import ApiError
from prompts.models import Prompt
from services.jobs import start_processing

from .models import Recording
from .serializers import RecordingSerializer, UploadSerializer
from .uploads import check_and_save_upload

STALE_MINUTES = 20


class RecordingViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    """Upload, list, status, delete, transcript and analysis of recordings."""

    serializer_class = RecordingSerializer
    throttle_scope = "uploads"

    def get_throttles(self):
        # Only uploads are rate limited.
        return [ScopedRateThrottle()] if self.action == "create" else []

    def get_queryset(self):
        # a recording stuck in "processing" for too long was interrupted (for example the server restarted)
        Recording.objects.filter(
            user=self.request.user,
            status=Recording.PROCESSING,
            created_at__lt=timezone.now() - timedelta(minutes=STALE_MINUTES),
        ).update(
            status=Recording.FAILED,
            error_code="interrupted",
            error_message="Processing was interrupted. Please upload the recording again.",
            completed_at=timezone.now(),
        )
        # only the logged in user's recordings
        queryset = Recording.objects.filter(user=self.request.user).select_related("analysis")
        prompt_id = self.request.query_params.get("prompt_id")
        if prompt_id:
            if not prompt_id.isdigit():
                raise ApiError(400, "validation_error", "prompt_id must be a number.")
            queryset = queryset.filter(prompt_id=int(prompt_id))
        return queryset

    def create(self, request):
        # refuse a huge upload before reading it
        limit = django_settings.MAX_UPLOAD_MB * 1024 * 1024 + 100 * 1024
        if int(request.META.get("CONTENT_LENGTH") or 0) > limit:
            raise ApiError(413, "file_too_large", "The file is larger than %s MB." % django_settings.MAX_UPLOAD_MB)

        form = UploadSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        settings = get_all_settings()

        prompt = None
        if "prompt_id" in form.validated_data:
            prompt = Prompt.objects.filter(id=form.validated_data["prompt_id"], is_active=True).first()
            if prompt is None:
                raise ApiError(400, "validation_error", "That prompt does not exist.")

        path, duration = check_and_save_upload(
            form.validated_data["audio"], settings["min_recording_seconds"], settings["max_recording_seconds"]
        )
        try:
            recording = Recording.objects.create(
                user=request.user,
                prompt=prompt,
                language=form.validated_data.get("language", settings["default_language"]),
                duration_sec=duration,
            )
        except Exception:
            path.unlink(missing_ok=True)
            raise

        start_processing(recording.id, str(path))
        return Response(
            {
                "id": recording.id,
                "status": Recording.PROCESSING,
                "created_at": DateTimeField().to_representation(recording.created_at),
            },
            status=status.HTTP_202_ACCEPTED,
        )

    def _require_completed(self, recording):
        if recording.status == Recording.PROCESSING:
            raise ApiError(409, "not_ready", "The recording is still being processed.")
        if recording.status == Recording.FAILED:
            raise ApiError(409, "recording_failed", recording.error_message or "Processing failed.")

    @action(detail=True, methods=["get"])
    def transcript(self, request, pk=None):
        recording = self.get_object()
        self._require_completed(recording)
        transcript = recording.transcript
        return Response(
            {
                "recording_id": recording.id,
                "full_text": transcript.full_text,
                "words": transcript.words,
                "engine": transcript.engine,
            }
        )

    @action(detail=True, methods=["get"])
    def analysis(self, request, pk=None):
        recording = self.get_object()
        self._require_completed(recording)
        return Response(breakdown_for_recording(recording))
