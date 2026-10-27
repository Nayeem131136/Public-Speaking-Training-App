"""/filler-words/  list, add, edit and remove filler words."""
from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.exceptions import PermissionDenied

from .models import FillerWord


class FillerWordSerializer(serializers.ModelSerializer):
    # personal (default) or global, only admins can add global
    scope = serializers.ChoiceField(choices=["personal", "global"], write_only=True, required=False, default="personal")

    class Meta:
        model = FillerWord
        fields = ["id", "word", "language", "is_active", "scope"]
        validators = []  # we check for duplicates ourselves in validate()

    def validate_word(self, value):
        value = value.strip().lower()
        if not value:
            raise serializers.ValidationError("The word cannot be empty.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        if self.instance is not None:
            owner = self.instance.owner
        else:
            owner = None if attrs.get("scope") == "global" else request.user

        word = attrs.get("word", self.instance.word if self.instance else None)
        language = attrs.get("language", self.instance.language if self.instance else "en")
        exists = FillerWord.objects.filter(word=word, language=language, owner=owner)
        if self.instance is not None:
            exists = exists.exclude(pk=self.instance.pk)
        if exists.exists():
            raise serializers.ValidationError({"word": "This word is already in the list."})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["scope"] = "global" if instance.owner_id is None else "personal"
        return data


class FillerWordViewSet(viewsets.ModelViewSet):
    serializer_class = FillerWordSerializer

    def get_queryset(self):
        queryset = FillerWord.objects.filter(Q(owner__isnull=True) | Q(owner=self.request.user))
        language = self.request.query_params.get("language")
        if language:
            queryset = queryset.filter(language=language)
        return queryset

    def _check_can_edit(self, word):
        if word.owner_id is None and not self.request.user.is_staff:
            raise PermissionDenied("Only admins can change global words.")

    def perform_create(self, serializer):
        scope = serializer.validated_data.pop("scope", "personal")
        if scope == "global":
            if not self.request.user.is_staff:
                raise PermissionDenied("Only admins can add global words.")
            serializer.save(owner=None)
        else:
            serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        self._check_can_edit(serializer.instance)
        serializer.validated_data.pop("scope", None)
        serializer.save()

    def perform_destroy(self, instance):
        self._check_can_edit(instance)
        instance.delete()
