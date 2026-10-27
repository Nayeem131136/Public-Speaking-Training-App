"""GET /settings/ and PATCH /settings/{key}/"""
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from config.exceptions import ApiError

from .defaults import CHOICES, DEFAULTS, DESCRIPTIONS
from .models import AppSetting
from .settings_store import get_all_settings


def validate_setting_value(key, value):
    """Make sure the new value has the same kind as the default one."""
    if isinstance(DEFAULTS[key], str):
        if not isinstance(value, str):
            raise ApiError(400, "validation_error", "%s must be text." % key)
        if key in CHOICES and value not in CHOICES[key]:
            raise ApiError(400, "validation_error", "%s must be one of: %s." % (key, ", ".join(CHOICES[key])))
        return value

    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ApiError(400, "validation_error", "%s must be a number greater than 0." % key)
    return value


class SettingsView(APIView):
    """Everyone can read the thresholds (the frontend needs the target pace)."""

    def get(self, request):
        return Response(get_all_settings())


class SettingDetailView(APIView):
    """Only admins can change them."""

    permission_classes = [IsAdminUser]

    def patch(self, request, key):
        if key not in DEFAULTS:
            raise NotFound("Unknown setting.")
        if "value" not in request.data:
            raise ApiError(400, "validation_error", 'Send the new value as {"value": ...}.')
        value = validate_setting_value(key, request.data["value"])
        row, _ = AppSetting.objects.update_or_create(
            key=key, defaults={"value": value, "description": DESCRIPTIONS[key]}
        )
        return Response({"key": key, "value": row.value})
