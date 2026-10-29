"""Consulta del estado actual de un envío(HU #14).

POST /api/consultar-estado-envio/
    {"cod_seguimiento": "SRFR-XXXXXXXX"}

El código se envía en el cuerpo y la respuesta solo contiene el estado del
paquete correspondiente. La app no envía el código ni conserva un historial.
"""

import json

from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.models import Paquete


@csrf_exempt  # Consulta pública de solo lectura; no depende de una sesión.
@never_cache  # Evita guardar la respuesta del seguimiento en cachés.
@require_POST
def consultar_estado_envio(request):
    """Devuelve únicamente el estado del paquete identificado por el código."""
    try:
        datos = json.loads(request.body or b"{}")
    except ValueError:
        return JsonResponse(
            {"message": "El cuerpo debe ser un objeto JSON válido."}, status=400
        )

    if not isinstance(datos, dict):
        return JsonResponse(
            {"message": "El cuerpo debe ser un objeto JSON válido."}, status=400
        )

    codigo = datos.get("cod_seguimiento")
    if not isinstance(codigo, str):
        return JsonResponse(
            {"message": "Ingresá un código de seguimiento válido."}, status=400
        )

    # Los códigos generados son ASCII; se aceptan minúsculas y espacios externos
    # para facilitar su ingreso. Se rechazan caracteres de control y textos más
    # largos que el campo de la base de datos.
    codigo = codigo.strip().upper()
    if not codigo or len(codigo) > 255 or not codigo.isascii() or not codigo.isprintable():
        return JsonResponse(
            {"message": "Ingresá un código de seguimiento válido."}, status=400
        )

    try:
        estado = Paquete.objects.values_list("estado", flat=True).get(
            cod_seguimiento=codigo
        )
    except Paquete.DoesNotExist:
        return JsonResponse(
            {"message": "No se encontró un envío con ese código de seguimiento."},
            status=404,
        )

    return JsonResponse({"estado": estado})
