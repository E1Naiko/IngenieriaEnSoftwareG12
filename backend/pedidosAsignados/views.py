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

from core.models import Paquete, Repartidor

# Con 404/403 + "message" el front cierra la sesión del repartidor.
MSG_SESION_INVALIDA = "Sesión inválida"
MSG_REPARTIDOR_BAJA = "Repartidor dado de baja"

# Pendiente = todavía sin asignar; entregado y cancelado ya no son suyos
# (el cancelado pasa a pedidos cercanos).
ESTADOS_ACTIVOS = [
    Paquete.Estado.ASIGNADO,
    Paquete.Estado.RETIRADO,
    Paquete.Estado.EN_CAMINO,
]


def _paquete_to_dict(paquete):
    return {
        "id": paquete.id,
        "cod_seguimiento": paquete.cod_seguimiento,
        "estado": paquete.estado.lower(),  # el front arma la clase CSS con este valor
        "tamanio": paquete.tamanio,
        "destinatario": f"{paquete.cliente.nombre} {paquete.cliente.apellido}".strip(),
        "direccion": paquete.cliente.direccion,
        "comercio": paquete.comercio.nombre,
        "fecha_destino": paquete.fecha_destino.isoformat(),
    }


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

    # Puede haber sido dado de baja después de loguearse
    if repartidor.estado == Repartidor.Estado.BAJA:
        return JsonResponse({"message": MSG_REPARTIDOR_BAJA}, status=403)

    # En la base hay estados en mayúsculas (datos DEV), por eso se compara en minúscula
    paquetes = (
        repartidor.paquetes.annotate(estado_min=Lower("estado"))
        .filter(estado_min__in=ESTADOS_ACTIVOS)
        .select_related("cliente", "comercio")
    )
    return JsonResponse({"paquetes": [_paquete_to_dict(p) for p in paquetes]})
