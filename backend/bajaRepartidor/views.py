from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods

from core.models import Repartidor


def _es_baja(estado: str) -> bool:
    return (estado or "").strip().lower() == Repartidor.Estado.BAJA.lower()


def _repartidor_to_dict(repartidor):
    return {
        "id": repartidor.id,
        "nombre": repartidor.nombre,
        "apellido": repartidor.apellido,
        "dni": repartidor.dni,
        "telefono": repartidor.telefono,
        "mail": repartidor.mail,
        "tipo_vehiculo": repartidor.tipo_vehiculo,
        "estado": repartidor.estado,
    }


@require_GET
def repartidor_detalle(request, repartidor_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "No autenticado"}, status=401)

    try:
        repartidor = Repartidor.objects.get(pk=repartidor_id)
    except Repartidor.DoesNotExist:
        return JsonResponse({"error": "Repartidor no encontrado"}, status=404)

    if _es_baja(repartidor.estado):
        return JsonResponse({"error": "El repartidor ya fue dado de baja"}, status=400)

    return JsonResponse({"repartidor": _repartidor_to_dict(repartidor)}, status=200)


@require_http_methods(["POST", "PATCH", "DELETE"])
def repartidor_baja(request, repartidor_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "No autenticado"}, status=401)

    try:
        repartidor = Repartidor.objects.get(pk=repartidor_id)
    except Repartidor.DoesNotExist:
        return JsonResponse({"error": "Repartidor no encontrado"}, status=404)

    if _es_baja(repartidor.estado):
        return JsonResponse({"error": "El repartidor ya fue dado de baja"}, status=400)

    Repartidor.objects.filter(pk=repartidor_id).update(estado=Repartidor.Estado.BAJA)
    repartidor.refresh_from_db()

    return JsonResponse(
        {
            "mensaje": "Repartidor dado de baja con éxito",
            "repartidor": _repartidor_to_dict(repartidor),
        },
        status=200,
    )