"""Vistas para actualizar el estado de los paquetes/pedidos (HU #34).

Dos caminos, con requisitos distintos:

- ``GET``: consulta pública (la usa la pantalla de seguimiento, HU #14). No
  pide credenciales y solo devuelve datos del paquete.
- ``POST``: lo usa el dashboard del **repartidor**. El backend no guarda
  sesión del repartidor, así que el ``token`` del cuerpo identifica a quien
  pide el cambio y se valida:

  * ``401`` si falta el token o no corresponde a ningún repartidor.
  * ``403`` si el repartidor está **dado de baja** (HU #38): en el front el
    dashboard cierra la sesión, pero un request directo tiene que rechazarse
    igual.
  * ``403`` si intenta modificar un paquete que **no tiene asignado**. El
    historial y la lista de pedidos del repartidor se arman con la FK
    ``paquete.repartidor``, así que sin esta verificación cualquiera con un
    token podía cambiar el estado de un paquete ajeno.
"""

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.estados import es_baja
from core.models import Paquete, Repartidor

MSG_TOKEN_FALTANTE = "Falta el token"
MSG_TOKEN_INVALIDO = "Token inválido"
MSG_REPARTIDOR_BAJA = (
    "El repartidor no se encuentra habilitado. Comuníquese con el coordinador"
)
MSG_PAQUETE_AJENO = "El paquete no está asignado a este repartidor"


def to_dict(paquete):
    """
    Convierte un objeto Paquete en un diccionario para enviar al frontend.
    """
    return {
        "id": paquete.id,
        "cod_seguimiento": paquete.cod_seguimiento,
        "estado": paquete.estado,
        "tamanio": paquete.tamanio,
        "fecha_origen": str(paquete.fecha_origen) if paquete.fecha_origen else None,
        "fecha_destino": str(paquete.fecha_destino) if paquete.fecha_destino else None,
        "id_repartidor_asignado": paquete.repartidor.id if paquete.repartidor else None,
        "nombre_repartidor": (
            f"{paquete.repartidor.nombre} {paquete.repartidor.apellido}".strip()
            if paquete.repartidor
            else None
        ),
        "id_comercio": paquete.comercio.id,
        "id_cliente": paquete.cliente.id,
    }


def _repartidor_por_token(token):
    """Busca al repartidor dueño de la petición. Devuelve (repartidor, error)."""
    if not token:
        return None, JsonResponse({"message": MSG_TOKEN_FALTANTE}, status=400)

    repartidor = Repartidor.objects.filter(token=token).first()
    if repartidor is None:
        return None, JsonResponse({"message": MSG_TOKEN_INVALIDO}, status=401)

    # core.estados normaliza el estado: en la base hay 'baja', 'BAJA' y
    # variantes con espacios (HU #38).
    if es_baja(repartidor.estado):
        return None, JsonResponse({"message": MSG_REPARTIDOR_BAJA}, status=403)

    return repartidor, None


def _paquete_del_repartidor(paquete, repartidor):
    """True si el repartidor es el asignado al paquete (comparación normalizada)."""
    return (
        paquete.repartidor_id is not None
        and paquete.repartidor_id == repartidor.id
    )


@csrf_exempt
@require_http_methods(["GET", "POST"])
def cambiar_estado_pedido(request):
    """
    GET /api/cambiar-estado-pedido/
        Lista todos los paquetes existentes.
        Opcional: ?cod_seguimiento=SRFR-XXXX para filtrar por uno específico.

    POST /api/cambiar-estado-pedido/
        Actualiza el estado de un paquete específico.
        Body JSON esperado: {"token": "...", "id": <id_paquete>, "estado": ...}
    """

    # --- GET: Listar paquetes ---
    if request.method == "GET":
        cod_seguimiento = request.GET.get("cod_seguimiento")

        if cod_seguimiento:
            paquetes = Paquete.objects.filter(cod_seguimiento=cod_seguimiento)
        else:
            paquetes = Paquete.objects.all()

        # Usamos .exists() para verificar si hay paquetes
        if not paquetes.exists():
            return JsonResponse(
                {"message": "No hay paquetes registrados.", "paquetes": []},
                status=200
            )

        lista_paquetes = [to_dict(p) for p in paquetes]
        return JsonResponse(
            {"message": "Paquetes obtenidos correctamente.", "paquetes": lista_paquetes},
            status=200
        )

    # --- POST: Actualizar estado de un paquete ---
    # Parsear JSON
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"message": "El cuerpo debe ser JSON válido."}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"message": "El cuerpo debe ser un objeto JSON."}, status=400)

    # Quién pide el cambio: el token del repartidor que tiene la sesión abierta
    # en el dashboard. Se normaliza como en loginRepartidor.
    token = str(data.get("token") or "").strip().upper()
    repartidor, error = _repartidor_por_token(token)
    if error is not None:
        return error

    # Obtener id y nuevo estado
    paquete_id = data.get("id")
    nuevo_estado = data.get("estado")

    if paquete_id is None:
        return JsonResponse({"message": "Falta el campo 'id' del paquete."}, status=400)

    if nuevo_estado is None:
        return JsonResponse({"message": "Falta el campo 'estado'."}, status=400)

    # Validar que el estado sea válido
    estados_validos = [e.value for e in Paquete.Estado]
    if nuevo_estado not in estados_validos:
        return JsonResponse(
            {"message": f"Estado inválido. Debe ser uno de: {', '.join(estados_validos)}"},
            status=400
        )

    # Buscar el paquete por ID
    paquetes = Paquete.objects.filter(id=paquete_id)

    # Usar .exists() para verificar si existe
    if not paquetes.exists():
        return JsonResponse(
            {"message": f"No se encontró un paquete con id={paquete_id}."},
            status=404
        )

    # Obtener el paquete y actualizar
    paquete = paquetes.first()

    # Solo el repartidor asignado puede cambiar el estado de su paquete.
    if not _paquete_del_repartidor(paquete, repartidor):
        return JsonResponse({"message": MSG_PAQUETE_AJENO}, status=403)

    # Validación extra: no se puede modificar un paquete ya entregado o cancelado
    if paquete.estado in [Paquete.Estado.ENTREGADO, Paquete.Estado.CANCELADO]:
        return JsonResponse(
            {"message": f"No se puede modificar el estado de un paquete '{paquete.estado}'."},
            status=400
        )

    paquete.estado = nuevo_estado
    paquete.save()

    return JsonResponse(
        {
            "message": "Estado del paquete actualizado correctamente.",
            "paquete": to_dict(paquete),
        },
        status=200
    )
