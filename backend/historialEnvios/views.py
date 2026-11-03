"""

Historial de envios (HU #10).

El coordinador ve el historial en dos pasos:
  1) Lista de repartidores (historial_lista).
  2) Al elegir uno, el listado con todos sus pedidos (historial_repartidor).

El historial no tiene tablas propias: se arma leyendo la tabla `paquete`.
"""
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from core.models import Paquete, Repartidor  # Paquete se usa en comentarios; Repartidor en las consultas

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Estados de paquete que cuentan como "historial".
ESTADOS_HISTORIAL = ["entregado", "cancelado"]

# Mensajes de error.
MSG_NO_AUTORIZADO = "Solo el coordinador puede ver el historial."
MSG_NO_ENCONTRADO = "Repartidor no encontrado."


# ---------------------------------------------------------------------------
# Funciones auxiliares (empiezan con _ porque son de uso interno)
# ---------------------------------------------------------------------------

def _q_estados(prefijo=""):
    """
    Arma el filtro "el estado es entregado O cancelado", sin distinguir
    mayúsculas de minúsculas (ENTREGADO, Entregado y entregado valen igual).

    `__iexact` compara contra UN solo valor, así que no se puede pasar la lista
    entera: se arma un filtro por cada estado y se unen con OR (el símbolo |).

    `prefijo` sirve cuando el filtro se aplica desde otra tabla. Por ejemplo,
    desde Repartidor el campo se llama "paquetes__estado", así que se pasa
    prefijo="paquetes__". Desde Paquete se deja vacío.
    """
    q = Q()  # arranca vacío
    for estado in ESTADOS_HISTORIAL:
        q |= Q(**{f"{prefijo}estado__iexact": estado})
    return q


def _solo_coordinador(request):
    """
    Controla que haya una sesión iniciada. Como hay un único coordinador,
    alcanza con estar logueado.

    Devuelve un error 401 (listo para retornar) si NO hay sesión,
    o None si todo está bien y la vista puede seguir.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"message": MSG_NO_AUTORIZADO}, status=401)
    return None


def _paquete_to_dict(paquete):
    """
    Convierte un Paquete en un diccionario simple para devolverlo como JSON.
    Es lo que el front va a mostrar en cada renglón del historial.
    """
    return {
        "id": paquete.id,
        "cod_seguimiento": paquete.cod_seguimiento,
        "estado": paquete.estado.lower(),  # siempre en minúsculas para el front
        # Las fechas se pasan a texto "2026-10-29"; si faltan, devuelve None (null en JSON)
        "fecha_origen": paquete.fecha_origen.isoformat() if paquete.fecha_origen else None,
        "fecha_destino": paquete.fecha_destino.isoformat() if paquete.fecha_destino else None,
        "comercio": paquete.comercio.nombre,
        "cliente": f"{paquete.cliente.apellido}, {paquete.cliente.nombre}",
        "direccion": paquete.cliente.direccion,
        # TODO (HU #13): cuando el modelo tenga estos campos, agregarlos acá:
        # "motivo_cancelacion": paquete.motivo_cancelacion,

    }


# ---------------------------------------------------------------------------
# Vistas (las funciones que responden a cada URL)
# ---------------------------------------------------------------------------

@require_GET  # solo acepta GET; cualquier otro método responde 405
def historial_lista(request):
    """
    Escenario 1 — GET /api/historial/

    Devuelve todos los repartidores (también los dados de baja) con la
    cantidad de pedidos de su historial. El front muestra esta lista y,
    al elegir uno, pide el detalle con historial_repartidor.
    """
    # 1) Controlar la sesión: si falta, se corta con el 401
    error = _solo_coordinador(request)
    if error:
        return error

    # 2) Traer todos los repartidores y, a cada uno, agregarle un campo
    #    calculado "cantidad_envios" = cuántos de sus paquetes cumplen el filtro.
    repartidores = Repartidor.objects.annotate(
        cantidad_envios=Count("paquetes", filter=_q_estados("paquetes__"))
    )

    # 3) Armar la lista que se devuelve
    results = [
        {
            "id": r.id,
            "nombre": r.nombre,
            "apellido": r.apellido,
            "dado_de_baja": r.estado.lower() == "baja",  # el estado activo/inactivo no se muestra
            "cantidad_envios": r.cantidad_envios,
        }
        for r in repartidores
    ]
    return JsonResponse({"results": results, "count": len(results)})


@require_GET
def historial_repartidor(request, pk):
    """
    Escenario 2 — GET /api/historial/<id>/

    Devuelve el historial completo de UN repartidor: sus pedidos entregados
    y cancelados, del más reciente al más viejo.

    `pk` es el id del repartidor y viene de la URL (ver urls.py).
    """
    # 1) Controlar la sesión
    error = _solo_coordinador(request)
    if error:
        return error

    # 2) Buscar al repartidor. .first() devuelve el objeto o None si no existe
    #    (así no hace falta un try/except).
    repartidor = Repartidor.objects.filter(pk=pk).first()
    if repartidor is None:
        return JsonResponse({"message": MSG_NO_ENCONTRADO}, status=404)

    # 3) Sus paquetes (relación inversa "paquetes") que cumplen el filtro.
    #    select_related trae comercio y cliente en la misma consulta, para no
    #    hacer una consulta extra por cada paquete.
    #    Orden: primero la fecha de destino más reciente; si empatan, el id más alto.
    paquetes = (
        repartidor.paquetes.filter(_q_estados())
        .select_related("comercio", "cliente")
        .order_by("-fecha_destino", "-id")
    )

    # 4) Convertir cada paquete a diccionario y responder
    results = [_paquete_to_dict(p) for p in paquetes]
    return JsonResponse(
        {
            "repartidor": {
                "id": repartidor.id,
                "nombre": repartidor.nombre,
                "apellido": repartidor.apellido,
                "dado_de_baja": repartidor.estado.lower() == "baja",
            },
            "results": results,
            "count": len(results),
        }
    )