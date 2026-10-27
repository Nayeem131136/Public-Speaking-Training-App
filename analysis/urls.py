from django.urls import path

from .views import ProgressView

urlpatterns = [path("progress/", ProgressView.as_view())]
