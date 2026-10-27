from django.contrib import admin

from .models import Category, Prompt


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name"]


@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "difficulty", "language", "is_active"]
    list_filter = ["category", "difficulty", "language", "is_active"]
    search_fields = ["title", "text"]
