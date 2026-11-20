"""
Pedidos asignados al repartidor (HU #17).

    POST /api/paquetes-repartidor/   body: {"token": "ABC123"}

El repartidor ya está logueado, pero el backend no guarda sesión: el token
que el front tiene en localStorage es lo único que identifica quién pide la
lista. Responde ``{"paquetes": [...]}`` con el contrato que consume
``frontend/src/pages/Dashboardrepartidor.tsx``; lista vacía = escenario 2.
"""

import json

from django.db.models.functions import Lower
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.estados import es_baja
from core.models import Paquete, Repartidor
from .serializers import paquete_to_dict

# Con 404/403 + "message" el front cierra la sesión del repartidor.
MSG_SESION_INVALIDA = "Sesión inválida"
MSG_REPARTIDOR_BAJA = "Repartidor dado de baja"

# Pedidos bajo responsabilidad del repartidor, incluidos los que debe devolver.
# ``cancelado_por_cliente`` también sigue a su cargo hasta que lo entregue en
# el comercio: no se reasigna, lo lleva de vuelta a su origen.
ESTADOS_ACTIVOS = [
    Paquete.Estado.ASIGNADO,
    Paquete.Estado.RETIRADO,
    Paquete.Estado.EN_CAMINO,
    Paquete.Estado.EN_DEVOLUCION,
    Paquete.Estado.CANCELADO_POR_CLIENTE,
]


@csrf_exempt  # el front del repartidor no maneja token CSRF
@require_POST
def paquetes_repartidor(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        data = None
    if not isinstance(data, dict):
        return JsonResponse({"message": "El cuerpo debe ser JSON válido."}, status=400)

    token = str(data.get("token") or "").strip().upper()
    if not token:
        return JsonResponse({"message": "Falta el token"}, status=400)

    try:
        repartidor = Repartidor.objects.get(token=token)
    except Repartidor.DoesNotExist:
        return JsonResponse({"message": MSG_SESION_INVALIDA}, status=404)

    # Puede haber sido dado de baja después de loguearse (HU #38)
    if es_baja(repartidor.estado):
        return JsonResponse({"message": MSG_REPARTIDOR_BAJA}, status=403)

    # En la base hay estados en mayúsculas (datos DEV), por eso se compara en minúscula
    paquetes = (
        repartidor.paquetes.annotate(estado_min=Lower("estado"))
        .filter(estado_min__in=ESTADOS_ACTIVOS)
        .select_related("cliente", "comercio")
    )
    return JsonResponse({"paquetes": [paquete_to_dict(p) for p in paquetes]})
