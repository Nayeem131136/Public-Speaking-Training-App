from rest_framework import serializers

from .models import Category, Prompt


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class PromptSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Prompt
        fields = ["id", "category", "category_name", "title", "text", "difficulty", "suggested_seconds", "language"]
