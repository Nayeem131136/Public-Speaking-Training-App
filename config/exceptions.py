"""One error format for every error: {"error": {"code": ..., "message": ...}}"""
from django.http import Http404
from rest_framework import exceptions
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class ApiError(APIException):
    """Raise this anywhere to return a clean error with our own code."""

    def __init__(self, status_code, code, message):
        super().__init__(detail=message)
        self.status_code = status_code
        self.error_code = code


# Default code for the errors that DRF raises by itself.
CODES = [
    (exceptions.NotAuthenticated, "unauthorized"),
    (exceptions.AuthenticationFailed, "unauthorized"),
    (exceptions.PermissionDenied, "forbidden"),
    (exceptions.NotFound, "not_found"),
    (Http404, "not_found"),
    (exceptions.ValidationError, "validation_error"),
    (exceptions.MethodNotAllowed, "method_not_allowed"),
    (exceptions.Throttled, "too_many_requests"),
    (exceptions.UnsupportedMediaType, "unsupported_media_type"),
    (exceptions.ParseError, "bad_request"),
]


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:  # a real server error, let Django handle it
        return None

    if isinstance(exc, ApiError):
        code, message, fields = exc.error_code, str(exc.detail), None
    else:
        code = next((c for cls, c in CODES if isinstance(exc, cls)), "error")
        if isinstance(exc, exceptions.ValidationError):
            message, fields = "Some fields are not valid.", response.data
        else:
            data = response.data
            message = str(data.get("detail", exc)) if isinstance(data, dict) else str(data)
            fields = None

    body = {"error": {"code": code, "message": message}}
    if fields is not None:
        body["error"]["fields"] = fields
    response.data = body
    return response
