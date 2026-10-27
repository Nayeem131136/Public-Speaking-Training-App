from django.contrib import admin
from django.urls import include, path

handler404 = "config.views.not_found"
handler500 = "config.views.server_error"

urlpatterns = [
    path("", include("console.urls")),  # test page
    path("admin/", admin.site.urls),
    path("api/v1/", include("config.api_urls")),
    path("api-auth/", include("rest_framework.urls")),  # Login button in the browsable API
]
