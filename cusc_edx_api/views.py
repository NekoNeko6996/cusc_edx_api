from django.http import JsonResponse
from django.views.decorators.http import require_GET


def ping(request):
    """
    Endpoint test đơn giản.
    """
    return JsonResponse({"ok": True, "app": "cusc_edx_api"})
