"""Consulta pública de estado y transiciones del repartidor asignado."""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.models import Paquete, Repartidor
from core.reasignacion import ESTADOS_CANCELABLES, ubicacion_valida
from crudComercios.views import _parse_body


def to_dict(paquete):
    return {
        "id": paquete.id,
        "cod_seguimiento": paquete.cod_seguimiento,
        "estado": paquete.estado,
        "tamanio": paquete.tamanio,
        "fecha_origen": str(paquete.fecha_origen) if paquete.fecha_origen else None,
        "fecha_destino": str(paquete.fecha_destino) if paquete.fecha_destino else None,
        "id_repartidor_asignado": paquete.repartidor_id,
        "nombre_repartidor": (
            f"{paquete.repartidor.nombre} {paquete.repartidor.apellido}".strip()
            if paquete.repartidor else None
        ),
        "id_comercio": paquete.comercio_id,
        "id_cliente": paquete.cliente_id,
    }


def error(mensaje, status=400):
    return JsonResponse({"message": mensaje}, status=status)


def _cancelar(paquete, estado, data):
    causa = data.get("causa")
    motivo = data.get("motivo")
    if estado not in ESTADOS_CANCELABLES:
        return error("El pedido no está en condiciones de ser cancelado.", 409)
    if causa not in Paquete.CausaCancelacion.values:
        return error("Seleccioná una causa de cancelación válida.")
    if not isinstance(motivo, str) or not 1 <= len(motivo.strip()) <= 500 or "\x00" in motivo:
        return error("Indicá el motivo de la cancelación (máximo 500 caracteres).")

    ubicacion = ubicacion_valida(data.get("ubicacion"))
    if data.get("ubicacion") is not None and ubicacion is None:
        return error("La ubicación indicada no es válida.")

    paquete.causa_cancelacion = causa
    paquete.motivo_cancelacion = motivo.strip()
    paquete.retiro_latitud = paquete.retiro_longitud = None
    paquete.reasignacion_hasta = None
    if causa == Paquete.CausaCancelacion.FUERZA_MAYOR:
        paquete.estado = Paquete.Estado.PENDIENTE_REASIGNACION
        paquete.repartidor_original_id = paquete.repartidor_id
        paquete.repartidor_id = None
        ahora = timezone.now()
        # Sin un punto de retiro no podemos saber quién está cerca: pasa directo a la cola manual.
        paquete.reasignacion_hasta = ahora
        if ubicacion is not None:
            paquete.retiro_latitud, paquete.retiro_longitud = ubicacion
            paquete.reasignacion_hasta += timedelta(minutes=settings.REASIGNACION_MINUTOS)
        mensaje = (
            "El pedido se publicó en Pedidos cercanos."
            if ubicacion else "Sin ubicación de retiro: el pedido quedó disponible para el coordinador."
        )
    else:
        paquete.estado = Paquete.Estado.EN_DEVOLUCION
        mensaje = "Devolvé el paquete al comercio y confirmá la devolución."

    paquete.save(update_fields=[
        "estado", "causa_cancelacion", "motivo_cancelacion", "repartidor",
        "repartidor_original", "reasignacion_hasta", "retiro_latitud", "retiro_longitud",
    ])
    return JsonResponse({"message": mensaje, "paquete": to_dict(paquete)})


@csrf_exempt  # Las escrituras se autentican con el token del repartidor, no con cookies.
@require_http_methods(["GET", "POST"])
def cambiar_estado_pedido(request):
    if request.method == "GET":
        paquetes = Paquete.objects.select_related("repartidor")
        if codigo := request.GET.get("cod_seguimiento"):
            paquetes = paquetes.filter(cod_seguimiento=codigo)
        lista = [to_dict(p) for p in paquetes]
        mensaje = "Paquetes obtenidos correctamente." if lista else "No hay paquetes registrados."
        return JsonResponse({"message": mensaje, "paquetes": lista})

    data = _parse_body(request)
    if data is None:
        return error("El cuerpo debe ser un objeto JSON válido.")
    paquete_id, nuevo_estado = data.get("id"), data.get("estado")
    if paquete_id is None:
        return error("Falta el campo 'id' del paquete.")
    if type(paquete_id) is not int or not 0 < paquete_id <= 2147483647:
        return error("ID de paquete inválido.")
    if nuevo_estado is None:
        return error("Falta el campo 'estado'.")
    if nuevo_estado not in Paquete.Estado.values:
        return error("Estado inválido.")

    token = str(data.get("token") or "").strip().upper()
    repartidor = Repartidor.objects.filter(token=token).first() if token else None
    if repartidor is None:
        return error("Sesión inválida.", 401)
    if repartidor.estado.strip().lower() == Repartidor.Estado.BAJA:
        return error("Repartidor dado de baja.", 403)

    with transaction.atomic():
        paquete = Paquete.objects.select_for_update().filter(pk=paquete_id).first()
        if paquete is None:
            return error(f"No se encontró un paquete con id={paquete_id}.", 404)
        if paquete.repartidor_id != repartidor.pk:
            return error("El pedido no está asignado a este repartidor.", 403)

        estado = paquete.estado.strip().lower()
        if estado in (Paquete.Estado.ENTREGADO, Paquete.Estado.CANCELADO):
            return error(f"No se puede modificar el estado de un paquete '{paquete.estado}'.")
        if nuevo_estado == Paquete.Estado.CANCELADO and estado != Paquete.Estado.EN_DEVOLUCION:
            return _cancelar(paquete, estado, data)

        siguiente = {
            Paquete.Estado.ASIGNADO: Paquete.Estado.EN_CAMINO,
            Paquete.Estado.RETIRADO: Paquete.Estado.EN_CAMINO,
            Paquete.Estado.EN_CAMINO: Paquete.Estado.ENTREGADO,
            Paquete.Estado.EN_DEVOLUCION: Paquete.Estado.CANCELADO,
        }
        if nuevo_estado != siguiente.get(estado):
            return error("No se puede modificar el pedido a ese estado.", 409)

        paquete.estado = nuevo_estado
        campos = ["estado"]
        if nuevo_estado == Paquete.Estado.ENTREGADO:
            paquete.retiro_latitud = paquete.retiro_longitud = None
            campos += ["retiro_latitud", "retiro_longitud"]
        paquete.save(update_fields=campos)
        return JsonResponse({
            "message": "Devolución al comercio confirmada." if estado == Paquete.Estado.EN_DEVOLUCION
            else "Estado del paquete actualizado correctamente.",
            "paquete": to_dict(paquete),
        })
