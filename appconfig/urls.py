from django.urls import path
from rest_framework.routers import SimpleRouter

from .filler_api import FillerWordViewSet
from .settings_api import SettingDetailView, SettingsView

router = SimpleRouter()
router.register("filler-words", FillerWordViewSet, basename="filler-word")

urlpatterns = [
    path("settings/", SettingsView.as_view()),
    path("settings/<str:key>/", SettingDetailView.as_view()),
] + router.urls
