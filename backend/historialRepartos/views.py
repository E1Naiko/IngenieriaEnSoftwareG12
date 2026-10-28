"""
Historial de repartos (HU: el coordinador ve el historial de cada repartidor).

Rutas (se montan bajo el prefijo global ``/api/`` de ``config/urls.py``):

    GET /api/historial/       → escenario 1: listado de repartidores con el
                                 resumen de su historial (es el selector que
                                 usa la pantalla al presionar "historial").
    GET /api/historial/<id>/  → escenario 2: historial completo del repartidor
                                 elegido.

Reglas de la HU que resuelve este módulo
----------------------------------------
- **Solo el coordinador puede ver el historial.** El coordinador es el único
  rol con cuenta de Django (``loginCoordinador``, HU #4, que deja la cookie de
  sesión); el repartidor entra con su token (``loginRepartidor``, HU #9) y no
  tiene sesión. Por eso alcanza con exigir ``request.user.is_authenticated``:
  un repartidor nunca puede pasar. Sin sesión la API responde ``401``.
- **Hay un historial por cada repartidor.** El endpoint del escenario 2 nunca
  mezcla repartidores: lee la relación inversa ``paquete.repartidor`` de ese
  repartidor y nada más. El historial son los paquetes con estado
  ``entregado`` (misma definición que la property
  ``core.models.Repartidor.historial_asociado``); los estados ``pendiente``,
  ``retirado``, ``en_camino`` y ``cancelado`` todavía no son parte del
  historial, así que no aparecen.

Contrato JSON
-------------
Listado (escenario 1)::

    {
        "repartidores": [
            {
                "id": 3,
                "nombre": "Juan",
                "apellido": "Gómez",
                "dni": 40111222,
                "telefono": "221-555-0300",
                "mail": "juan@example.com",
                "tipo_vehiculo": "moto",
                "estado": "activo",
                "entregas": 2,                  # paquetes entregados
                "ultima_entrega": "2026-10-27"  # o null si no tiene entregas
            }
        ],
        "total_repartidores": 1
    }

Historial de un repartidor (escenario 2)::

    {
        "repartidor": { ...los mismos datos personales del listado... },
        "entregas": [
            {
                "id": 7,
                "cod_seguimiento": "SRFR-1A2B3C4D",
                "estado": "entregado",
                "tamanio": "chico",
                "comercio": "Kiosco Central",
                "destinatario": "Ana Pérez",
                "direccion": "Calle 12 #34",
                "fecha_origen": "2026-10-20",
                "fecha_destino": "2026-10-27",
                "comprobante": "/media/comprobantes/2026/10/foto.jpg"  # o null
            }
        ],
        "total_entregas": 1
    }

Los valores son primitivos (textos, números y fechas ISO): las FKs del modelo
son objetos Django y no se pueden devolver directamente en un ``JsonResponse``.
``comprobante`` es la URL relativa al backend del archivo que acredita la
entrega, o ``null`` si todavía no se subió. ``estado`` (del repartidor y del
paquete) y ``tipo_vehiculo`` se normalizan a minúsculas porque la columna es
un ``varchar`` libre y la base de desarrollo tiene valores en mayúscula (mismo
criterio que ``repartidoresDisponibles``).
"""

from django.db.models import Count, Max, Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.models import Paquete, Repartidor

# Texto de la regla "solo el Coordinador puede ver el historial".
MSG_SOLO_COORDINADOR = "Solo el coordinador puede ver el historial."
# El listado puede quedar vacío si todavía no se dio de alta ningún repartidor.
MSG_NO_HAY_REPARTIDORES = "No hay repartidores registrados en este momento."
# Un repartidor recién creado no tiene entregas: el historial existe, pero vacío.
MSG_SIN_ENTREGAS = "Este repartidor todavía no tiene entregas."
# El id del URL no corresponde a ningún repartidor de la base.
MSG_REPARTIDOR_NO_ENCONTRADO = "Repartidor no encontrado."

# Los estados se guardan en un varchar libre; se comparan sin distinguir
# mayúsculas para que los datos históricos ("ENTREGADO") también cuenten.
ESTADO_ENTREGADO = Paquete.Estado.ENTREGADO
# Filtro que marca, en las agregaciones del listado, un paquete ya entregado.
FILTRO_ENTREGADO = Q(paquetes__estado__iexact=ESTADO_ENTREGADO)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _es_coordinador(user) -> bool:
    """``True`` si la petición viene de una sesión de coordinador.

    El coordinador es el único rol con cuenta de Django (``loginCoordinador``)
    y, por lo tanto, el único que puede tener ``request.user`` autenticado: el
    repartidor se identifica con un token y no inicia sesión. Si en el futuro
    se agregan más roles con usuario de Django, este es el único punto a
    cambiar (por ejemplo, para exigir un permiso o un grupo).
    """
    return bool(user and user.is_authenticated)


def _sin_sesion() -> JsonResponse:
    """Respuesta ``401`` que pide iniciar sesión como coordinador."""
    return JsonResponse({"message": MSG_SOLO_COORDINADOR}, status=401)


def _normalizar(valor) -> str:
    """Texto en minúsculas y sin espacios sobrantes (estado, tipo de vehículo)."""
    return str(valor or "").strip().lower()


def _nombre_completo(persona) -> str:
    """Nombre + apellido de un ``Cliente``, sin espacios sobrantes."""
    return f"{persona.nombre} {persona.apellido}".strip()


def _repartidor_to_dict(repartidor) -> dict:
    """Datos personales del repartidor, comunes al listado y al detalle."""
    return {
        "id": repartidor.id,
        "nombre": repartidor.nombre,
        "apellido": repartidor.apellido,
        "dni": repartidor.dni,
        "telefono": repartidor.telefono,
        "mail": repartidor.mail,
        "tipo_vehiculo": _normalizar(repartidor.tipo_vehiculo),
        "estado": _normalizar(repartidor.estado),
    }


def _resumen_to_dict(repartidor) -> dict:
    """Ítem del listado: los datos del repartidor más el resumen del historial.

    ``entregas`` y ``ultima_entrega`` vienen de las anotaciones del queryset
    (``Count``/``Max`` con ``FILTRO_ENTREGADO``), así que no disparan consultas
    por repartidor.
    """
    data = _repartidor_to_dict(repartidor)
    data["entregas"] = repartidor.entregas
    data["ultima_entrega"] = (
        repartidor.ultima_entrega.isoformat()
        if repartidor.ultima_entrega
        else None
    )
    return data


def _entrega_to_dict(paquete) -> dict:
    """Un pedido entregado, tal como lo muestra el historial del repartidor."""
    comprobante = None
    if paquete.comprobante is not None and paquete.comprobante.file:
        # URL relativa al backend (/media/...): el front la resuelve contra el
        # mismo origen que el resto de la API.
        comprobante = paquete.comprobante.file.url

    return {
        "id": paquete.id,
        "cod_seguimiento": paquete.cod_seguimiento,
        "estado": _normalizar(paquete.estado),
        "tamanio": paquete.tamanio,
        "comercio": paquete.comercio.nombre,
        "destinatario": _nombre_completo(paquete.cliente),
        "direccion": paquete.cliente.direccion,
        "fecha_origen": paquete.fecha_origen.isoformat(),
        "fecha_destino": paquete.fecha_destino.isoformat(),
        "comprobante": comprobante,
    }


# ---------------------------------------------------------------------------
# Vistas
# ---------------------------------------------------------------------------

@csrf_exempt  # solo lectura: así un POST llega al 405 y no lo frena el CSRF (403)
@require_http_methods(["GET"])
def historial_repartidores(request):
    """Escenario 1: listado de repartidores con el resumen de su historial.

    ``GET /api/historial/``

    Es la pantalla a la que llega el coordinador al presionar "historial".
    Trae a todos los repartidores (también los ``inactivo`` y ``baja``: su
    historial no se borra cuando dejan la flota) con la cantidad de pedidos
    entregados y la fecha de la última entrega, ordenados por apellido y
    nombre.

    Respuestas:
    - 200: listado (con o sin repartidores, siempre con ``repartidores``).
    - 401: no hay sesión de coordinador.
    - 405: se utilizó un método HTTP no permitido.
    """
    if not _es_coordinador(request.user):
        return _sin_sesion()

    # Dos agregaciones en la misma consulta: cuántos paquetes entregó y cuándo
    # fue la última entrega. El filtro por estado va dentro del agregado para
    # que un repartidor sin entregas aparezca con 0 y no desaparezca del INNER
    # JOIN. El ordering del modelo (apellido, nombre) se mantiene.
    repartidores = Repartidor.objects.annotate(
        entregas=Count("paquetes", filter=FILTRO_ENTREGADO),
        ultima_entrega=Max("paquetes__fecha_destino", filter=FILTRO_ENTREGADO),
    )

    data = [_resumen_to_dict(repartidor) for repartidor in repartidores]

    if not data:
        return JsonResponse(
            {
                "mensaje": MSG_NO_HAY_REPARTIDORES,
                "repartidores": [],
                "total_repartidores": 0,
            },
            status=200,
        )

    return JsonResponse(
        {"repartidores": data, "total_repartidores": len(data)},
        status=200,
    )


@csrf_exempt  # solo lectura: así un POST llega al 405 y no lo frena el CSRF (403)
@require_http_methods(["GET"])
def historial_repartidor(request, pk):
    """Escenario 2: historial completo del repartidor elegido.

    ``GET /api/historial/<pk>/``

    Devuelve solo los pedidos entregados **de ese repartidor**, del más
    reciente al más viejo (``fecha_destino`` y, a igualdad, el último
    cargado). Un repartidor sin entregas responde ``200`` con la lista vacía y
    un mensaje, que no es lo mismo que un repartidor inexistente (``404``).

    Respuestas:
    - 200: historial del repartidor (puede estar vacío).
    - 401: no hay sesión de coordinador.
    - 404: no existe un repartidor con ese id.
    - 405: se utilizó un método HTTP no permitido.
    """
    if not _es_coordinador(request.user):
        return _sin_sesion()

    repartidor = Repartidor.objects.filter(pk=pk).first()
    if repartidor is None:
        return JsonResponse({"detail": MSG_REPARTIDOR_NO_ENCONTRADO}, status=404)

    # La property del modelo ya filtra los entregados de este repartidor
    # (historial_asociado usa paquete.repartidor). select_related resuelve
    # cliente, comercio y comprobante en el mismo query: el listado no hace una
    # consulta extra por entrega.
    historial = (
        repartidor.historial_asociado
        .select_related("cliente", "comercio", "comprobante")
        .order_by("-fecha_destino", "-id")
    )
    entregas = [_entrega_to_dict(paquete) for paquete in historial]

    respuesta = {
        "repartidor": _repartidor_to_dict(repartidor),
        "entregas": entregas,
        "total_entregas": len(entregas),
    }
    if not entregas:
        respuesta["mensaje"] = MSG_SIN_ENTREGAS

    return JsonResponse(respuesta, status=200)
