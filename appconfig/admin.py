from django.contrib import admin

from .models import AppSetting, FillerWord


@admin.register(FillerWord)
class FillerWordAdmin(admin.ModelAdmin):
    list_display = ["word", "language", "owner", "is_active"]
    list_filter = ["language", "is_active"]
    search_fields = ["word"]


@admin.register(AppSetting)
class AppSettingAdmin(admin.ModelAdmin):
    list_display = ["key", "value", "description"]
