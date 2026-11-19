from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from core.models import Repartidor


def _repartidor_to_dict(repartidor):
    """Serializa los datos del repartidor a diccionario para responder en JSON."""
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
    """Devuelve los datos del repartidor para el modal de confirmación."""
    try:
        repartidor = Repartidor.objects.get(pk=repartidor_id)
    except Repartidor.DoesNotExist:
        return JsonResponse({"error": "Repartidor no encontrado"}, status=404)

    if repartidor.estado == Repartidor.Estado.BAJA:
        return JsonResponse({"error": "El repartidor ya fue dado de baja"}, status=400)

    return JsonResponse({"repartidor": _repartidor_to_dict(repartidor)}, status=200)


@csrf_exempt
@require_http_methods(["POST", "PATCH", "DELETE"])
def repartidor_baja(request, repartidor_id):
    """Da de baja lógica al repartidor (estado='baja') cuando el coordinador confirma."""
    try:
        repartidor = Repartidor.objects.get(pk=repartidor_id)
    except Repartidor.DoesNotExist:
        return JsonResponse({"error": "Repartidor no encontrado"}, status=404)

    if repartidor.estado == Repartidor.Estado.BAJA:
        return JsonResponse({"error": "El repartidor ya fue dado de baja"}, status=400)

    # .update() cambia el estado sin disparar Repartidor.save() (que regeneraría el token)
    Repartidor.objects.filter(pk=repartidor_id).update(estado=Repartidor.Estado.BAJA)
    repartidor.refresh_from_db()

    return JsonResponse(
        {
            "mensaje": "Repartidor dado de baja con éxito",
            "repartidor": _repartidor_to_dict(repartidor),
        },
        status=200,
    )