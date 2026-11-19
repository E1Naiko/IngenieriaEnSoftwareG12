"""
Pedidos asignados al repartidor (HU #17).

    POST /api/paquetes-repartidor/   body: {"token": "ABC123"}

El repartidor ya está logueado, pero el backend no guarda sesión: el token
que el front tiene en localStorage es lo único que identifica quién pide la
lista. Responde ``{"paquetes": [...]}`` con el contrato que consume
``frontend/src/pages/Dashboardrepartidor.tsx``; lista vacía = escenario 2.
"""

import json

from django.db import transaction
from django.db.models.functions import Lower
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.models import Paquete, Repartidor
from core.reasignacion import ESTADOS_DISPONIBLES, distancia_oferta, ubicacion_valida
from crudComercios.views import _parse_body

# Con 404/403 + "message" el front cierra la sesión del repartidor.
MSG_SESION_INVALIDA = "Sesión inválida"
MSG_REPARTIDOR_BAJA = "Repartidor dado de baja"

# Pedidos bajo responsabilidad del repartidor, incluidos los que debe devolver.
ESTADOS_ACTIVOS = [
    Paquete.Estado.ASIGNADO,
    Paquete.Estado.RETIRADO,
    Paquete.Estado.EN_CAMINO,
    Paquete.Estado.EN_DEVOLUCION,
]


def _paquete_to_dict(paquete):
    data = {
        "id": paquete.id,
        "cod_seguimiento": paquete.cod_seguimiento,
        "estado": paquete.estado.lower(),  # el front arma la clase CSS con este valor
        "tamanio": paquete.tamanio,
        "destinatario": f"{paquete.cliente.nombre} {paquete.cliente.apellido}".strip(),
        "direccion": paquete.cliente.direccion,
        "comercio": paquete.comercio.nombre,
        "fecha_destino": paquete.fecha_destino.isoformat(),
    }

    if paquete.estado.lower() == Paquete.Estado.EN_DEVOLUCION:
        data["direccion_comercio"] = paquete.comercio.direccion
    if paquete.retiro_latitud is not None and paquete.retiro_longitud is not None:
        data["retiro"] = {"latitud": paquete.retiro_latitud, "longitud": paquete.retiro_longitud}
    return data


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


@csrf_exempt
@require_POST
def pedidos_cercanos(request):
    """Lista ofertas elegibles o toma una (si se envía id), usando el punto de retiro."""
    data = _parse_body(request)
    if data is None:
        return JsonResponse({"message": "El cuerpo debe ser un objeto JSON válido."}, status=400)
    token = str(data.get("token") or "").strip().upper()
    repartidor = Repartidor.objects.filter(token=token).first() if token else None
    if repartidor is None:
        return JsonResponse({"message": MSG_SESION_INVALIDA}, status=401)
    if repartidor.estado.strip().upper() not in ESTADOS_DISPONIBLES:
        return JsonResponse({"message": "El repartidor no está disponible."}, status=403)

    ubicacion = ubicacion_valida(data.get("ubicacion"))
    if ubicacion is None:
        return JsonResponse({"message": "Indicá una ubicación válida para ver los pedidos cercanos."}, status=400)

    if "id" in data:
        pk = data["id"]
        if type(pk) is not int or not 0 < pk <= 2147483647:
            return JsonResponse({"message": "ID de paquete inválido."}, status=400)
        with transaction.atomic():
            paquete = Paquete.objects.select_for_update().filter(pk=pk).first()
            if paquete is None or distancia_oferta(paquete, repartidor, ubicacion, timezone.now()) is None:
                return JsonResponse({"message": "El pedido ya no está disponible para vos."}, status=409)
            paquete.repartidor = repartidor
            paquete.estado = Paquete.Estado.ASIGNADO
            paquete.reasignacion_hasta = None
            paquete.save(update_fields=["repartidor", "estado", "reasignacion_hasta"])
            return JsonResponse({"message": "Pedido tomado.", "paquete": _paquete_to_dict(paquete)})

    ahora = timezone.now()
    if repartidor.tamanio_maximo_nivel is None:
        return JsonResponse({"paquetes": []})
    paquetes = Paquete.objects.filter(
        estado=Paquete.Estado.PENDIENTE_REASIGNACION,
        repartidor__isnull=True,
        reasignacion_hasta__gt=ahora,
        tamanio_nivel__lte=repartidor.tamanio_maximo_nivel,
    ).exclude(repartidor_original=repartidor)
    ofertas = []
    for paquete in paquetes:
        distancia = distancia_oferta(paquete, repartidor, ubicacion, ahora)
        if distancia is not None:
            ofertas.append({
                "id": paquete.id,
                "tamanio": paquete.tamanio,
                "distancia_km": round(distancia, 1),
                "disponible_hasta": paquete.reasignacion_hasta,
            })
    return JsonResponse({"paquetes": sorted(ofertas, key=lambda oferta: oferta["distancia_km"])})
