from django.http import JsonResponse
from django.views import defaults


def not_found(request, exception):
    if request.path.startswith("/api/"):
        return JsonResponse({"error": {"code": "not_found", "message": "This address does not exist."}}, status=404)
    return defaults.page_not_found(request, exception)


def server_error(request):
    if request.path.startswith("/api/"):
        return JsonResponse({"error": {"code": "server_error", "message": "Something went wrong on the server."}}, status=500)
    return defaults.server_error(request)
