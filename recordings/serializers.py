from rest_framework import serializers


class UploadSerializer(serializers.Serializer):
    """The fields of POST /recordings/ (multipart form)."""

    audio = serializers.FileField()
    prompt_id = serializers.IntegerField(required=False)
    language = serializers.ChoiceField(choices=["en", "bn"], required=False)


class RecordingSerializer(serializers.Serializer):
    """Short view of a recording, used for the list and the status check."""

    id = serializers.IntegerField()
    status = serializers.CharField()
    prompt_id = serializers.IntegerField(allow_null=True)
    language = serializers.CharField()
    duration_sec = serializers.FloatField(allow_null=True)
    created_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True)

    def to_representation(self, recording):
        data = super().to_representation(recording)
        if recording.status == "completed":
            analysis = getattr(recording, "analysis", None)
            if analysis is not None:
                data["summary"] = {
                    "total_words": analysis.total_words,
                    "wpm": analysis.wpm,
                    "filler_count": analysis.filler_count,
                    "pause_count": analysis.pause_count,
                }
        elif recording.status == "failed":
            data["error"] = {"code": recording.error_code, "message": recording.error_message}
        return data
