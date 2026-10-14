from django.http import JsonResponse


def ping(request):
    """Endpoint mínimo para probar la conexión desde el frontend React."""
    return JsonResponse({"status": "ok", "proyecto": "login", "grupo": 12})
