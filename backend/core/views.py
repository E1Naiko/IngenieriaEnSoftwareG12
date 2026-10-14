"""Vistas de la API (las que consume el frontend React)."""

from django.http import JsonResponse


def ping(request):
    """
    GET /api/ping/

    Endpoint mínimo para probar la conexión: el frontend lo llama al
    arrancar y verifica que el backend responde JSON y que el CORS
    está bien configurado.
    """
    return JsonResponse({"status": "ok", "proyecto": "core", "grupo": 12})
