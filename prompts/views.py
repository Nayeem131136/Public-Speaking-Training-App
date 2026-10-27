from django.db.models import Q
from rest_framework import viewsets

from .models import Category, Prompt
from .serializers import CategorySerializer, PromptSerializer


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /categories/"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class PromptViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /prompts/?category=1&search=interview&language=en"""

    serializer_class = PromptSerializer

    def get_queryset(self):
        queryset = Prompt.objects.filter(is_active=True).select_related("category")
        params = self.request.query_params
        if params.get("category", "").isdigit():
            queryset = queryset.filter(category_id=int(params["category"]))
        if params.get("language"):
            queryset = queryset.filter(language=params["language"])
        if params.get("search"):
            queryset = queryset.filter(Q(title__icontains=params["search"]) | Q(text__icontains=params["search"]))
        return queryset
