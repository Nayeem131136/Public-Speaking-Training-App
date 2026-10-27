"""Every API address lives under /api/v1/."""
from django.urls import include, path

urlpatterns = [
    path("auth/", include("accounts.urls")),
    path("", include("prompts.urls")),
    path("", include("recordings.urls")),
    path("", include("analysis.urls")),
    path("", include("appconfig.urls")),
]
