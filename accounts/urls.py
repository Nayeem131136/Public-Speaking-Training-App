from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import LoginView, MeView, RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),  # returns access + refresh tokens
    path("refresh/", TokenRefreshView.as_view()),
    path("me/", MeView.as_view()),
]
