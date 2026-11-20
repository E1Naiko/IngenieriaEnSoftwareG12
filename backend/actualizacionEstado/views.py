"""Consulta pública de estado y transiciones del repartidor asignado."""

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.models import Paquete, Repartidor
from crudComercios.views import _parse_body
from verPedidosPorAsignar.services import (
    DESTINOS_CANCELACION,
    CancelacionInvalida,
    registrar_cancelacion,
)


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
        if estado in Paquete.ESTADOS_CERRADOS:
            return error(f"No se puede modificar el estado de un paquete '{paquete.estado}'.")
        confirmando_devolucion = (
            estado == Paquete.Estado.EN_DEVOLUCION
            and nuevo_estado == Paquete.Estado.CANCELADO
            and "causa" not in data
        )
        if nuevo_estado in DESTINOS_CANCELACION and not confirmando_devolucion:
            if "causa" in data:
                causa = data["causa"]
                if nuevo_estado != Paquete.Estado.CANCELADO or causa not in Paquete.CausaCancelacion.values:
                    return JsonResponse({"message": "Causa de cancelación inválida.", "campo": "causa"}, status=400)
                motivo = data.get("motivo")
                if not isinstance(motivo, str) or not motivo.strip():
                    return JsonResponse({"message": "Indicá el motivo de la cancelación.", "campo": "motivo"}, status=400)
                destino = {
                    Paquete.CausaCancelacion.FUERZA_MAYOR: Paquete.Estado.PENDIENTE_REASIGNACION,
                    Paquete.CausaCancelacion.CLIENTE_AUSENTE: Paquete.Estado.EN_DEVOLUCION,
                    Paquete.CausaCancelacion.CLIENTE_RECHAZA: Paquete.Estado.CANCELADO_POR_CLIENTE,
                }[causa]
            else:
                causa = DESTINOS_CANCELACION[nuevo_estado]
                motivo = data.get("motivo", "")
                destino = nuevo_estado
            try:
                mensaje = registrar_cancelacion(
                    paquete, causa=causa, motivo=motivo, destino=destino,
                    ubicacion_informada=data.get("ubicacion"),
                )
            except CancelacionInvalida as exc:
                respuesta = {"message": str(exc)}
                if exc.campo:
                    respuesta["campo"] = exc.campo
                return JsonResponse(respuesta, status=409 if exc.estado_incompatible else 400)
            return JsonResponse({"message": mensaje, "paquete": to_dict(paquete)})

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
        if nuevo_estado == Paquete.Estado.ENTREGADO or confirmando_devolucion:
            paquete.retiro_latitud = paquete.retiro_longitud = None
            campos += ["retiro_latitud", "retiro_longitud"]
        paquete.save(update_fields=campos)
        return JsonResponse({
            "message": "Devolución al comercio confirmada." if estado == Paquete.Estado.EN_DEVOLUCION
            else "Estado del paquete actualizado correctamente.",
            "paquete": to_dict(paquete),
        })
