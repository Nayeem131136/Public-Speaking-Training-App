from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import RegisterSerializer


class RegisterView(CreateAPIView):
    """POST /auth/register/"""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"


class LoginView(TokenObtainPairView):
    """POST /auth/login/ (same as simplejwt's view, with a rate limit)"""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class MeView(APIView):
    """GET /auth/me/  who am I, and am I an admin?"""

    def get(self, request):
        user = request.user
        return Response(
            {"id": user.id, "username": user.username, "email": user.email, "is_admin": user.is_staff},
            status=status.HTTP_200_OK,
        )
