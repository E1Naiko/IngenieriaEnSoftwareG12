"""Listados de reasignación para el coordinador y para repartidores cercanos."""

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from core.models import Repartidor
from crudComercios.views import _parse_body
from pedidosAsignados.serializers import paquete_to_dict

from .services import (
    ESTADOS_DISPONIBLES,
    ofertas_cercanas,
    pendientes_para_coordinador,
    tomar_oferta,
    ubicacion_valida,
)


@never_cache
@require_GET
def pedidos_por_reasignar(request):
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Iniciá sesión como coordinador."}, status=403)

    paquetes = pendientes_para_coordinador(timezone.now()).select_related("cliente")
    return JsonResponse({"paquetes": [
        {
            "id": paquete.pk,
            "cod_seguimiento": paquete.cod_seguimiento,
            "estado": paquete.estado,
            "tamanio": paquete.tamanio,
            "destinatario": f"{paquete.cliente.nombre} {paquete.cliente.apellido}".strip(),
            "direccion": paquete.cliente.direccion,
            "causa_cancelacion": paquete.causa_cancelacion,
            "motivo_cancelacion": paquete.motivo_cancelacion,
        }
        for paquete in paquetes
    ]})


@never_cache
@csrf_exempt  # Se autentica con el token del repartidor, no con cookies.
@require_POST
def pedidos_cercanos(request):
    """Lista ofertas elegibles o toma una (si se envía id), usando el punto de retiro."""
    data = _parse_body(request)
    if data is None:
        return JsonResponse({"message": "El cuerpo debe ser un objeto JSON válido."}, status=400)
    token = str(data.get("token") or "").strip().upper()
    repartidor = Repartidor.objects.filter(token=token).first() if token else None
    if repartidor is None:
        return JsonResponse({"message": "Sesión inválida"}, status=401)
    if repartidor.estado.strip().upper() not in ESTADOS_DISPONIBLES:
        return JsonResponse({"message": "El repartidor no está disponible."}, status=403)

    ubicacion = ubicacion_valida(data.get("ubicacion"))
    if ubicacion is None:
        return JsonResponse({"message": "Indicá una ubicación válida para ver los pedidos cercanos."}, status=400)

    if "id" in data:
        pk = data["id"]
        if type(pk) is not int or not 0 < pk <= 2147483647:
            return JsonResponse({"message": "ID de paquete inválido."}, status=400)
        paquete = tomar_oferta(pk, repartidor, ubicacion)
        if paquete is None:
            return JsonResponse({"message": "El pedido ya no está disponible para vos."}, status=409)
        return JsonResponse({"message": "Pedido tomado.", "paquete": paquete_to_dict(paquete)})

    return JsonResponse({"paquetes": [
        {
            "id": paquete.pk,
            "tamanio": paquete.tamanio,
            "distancia_km": round(distancia, 1),
            "disponible_hasta": paquete.reasignacion_hasta,
        }
        for distancia, paquete in ofertas_cercanas(repartidor, ubicacion, timezone.now())
    ]})
