from rest_framework.response import Response
from rest_framework.views import APIView

from config.exceptions import ApiError

from .models import AnalysisResult


class ProgressView(APIView):
    """A user's attempts over time, for a trend chart."""

    def get(self, request):
        results = AnalysisResult.objects.filter(
            recording__user=request.user, recording__status="completed"
        ).select_related("recording")

        prompt_id = request.query_params.get("prompt_id")
        if prompt_id:
            if not prompt_id.isdigit():
                raise ApiError(400, "validation_error", "prompt_id must be a number.")
            results = results.filter(recording__prompt_id=int(prompt_id))

        results = results.order_by("recording__created_at", "recording_id")
        return Response(
            {
                "results": [
                    {
                        "recording_id": r.recording_id,
                        "prompt_id": r.recording.prompt_id,
                        "created_at": r.recording.created_at,
                        "wpm": r.wpm,
                        "filler_count": r.filler_count,
                        "pause_count": r.pause_count,
                    }
                    for r in results
                ]
            }
        )
