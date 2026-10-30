"""
Asignar repartidor a un paquete (HU: asignar repartidores según vehículo y
disponibilidad).

Rutas (prefijo global ``/api/`` en ``config/urls.py``)::

    GET  /api/dashboard/asignar-repartidor/?paquete=<id>
    POST /api/dashboard/asignar-repartidor/

Reglas de la HU que implementa este módulo:

- Solo se ofrecen repartidores **disponibles** (estado ``ACTIVO`` o
  ``DISPONIBLE``, sin distinguir mayúsculas ni espacios).
- Solo se ofrecen repartidores cuyo vehículo alcanza el tamaño del paquete
  (``Repartidor.tamanio_maximo_nivel >= Paquete.tamanio_nivel``). Entre ellos
  el coordinador elige; no hay asignación automática.
- El repartidor **no acepta** el pedido: el coordinador lo asigna directamente.
  Al asignar, ``paquete.estado`` NO cambia; la actualización del estado pasa a
  ser responsabilidad del repartidor.

GET con ``?paquete=<id>``::

    200 → {"repartidores": [...]}                       (escenario 1)
    200 → {"mensaje": "No hay repartidores disponibles con el vehículo requerido",
           "repartidores": []}                          (escenario 2)
    400 → {"paquete": "Campo obligatorio *"}  o  {"paquete": "Paquete inválido."}
    404 → {"detail": "Paquete no encontrado."}

GET sin ``paquete``: lista todos los repartidores disponibles (sin filtrar por
vehículo), igual que antes.

POST con body ``{"paquete": 1, "repartidor": 2}``::

    200 → paquete asignado (escenario 1)
    400 → campos obligatorios, repartidor no disponible o vehículo insuficiente
    404 → paquete o repartidor inexistente
    409 → el paquete ya tiene repartidor o ya no está en curso
"""

from django.db import transaction
from django.db.models import CharField, F
from django.db.models.functions import Trim, Upper
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.models import Paquete, Repartidor
from crudComercios.views import _parse_body


# Mensajes que pide la HU y del resto de validaciones.
MSG_NO_HAY_REPARTIDORES_DISPONIBLES = (
    "No se encuentran repartidores disponibles en este momento."
)
MSG_NO_HAY_CON_VEHICULO = "No hay repartidores disponibles con el vehículo requerido"
MSG_OBLIGATORIO = "Campo obligatorio *"

# Estados en los que el paquete ya no puede recibir un repartidor.
# "entregado" es final; "cancelado" tampoco se asigna.
ESTADOS_NO_ASIGNABLES = {
    Paquete.Estado.ENTREGADO.upper(),
    Paquete.Estado.CANCELADO.upper(),
}

# Valores de ``Repartidor.estado`` que cuentan como disponibles. "DISPONIBLE"
# es el de la base actual; "ACTIVO" es el legado.
ESTADOS_DISPONIBLES = {
    Repartidor.Estado.ACTIVO.upper(),
    "DISPONIBLE",
}


def _repartidor_to_dict(repartidor):
    """
    Convierte un objeto Repartidor en un diccionario de Python.

    Django utiliza este diccionario para generar la respuesta JSON
    que recibirá el frontend desarrollado con React.
    """
    return {
        # Identificador único del repartidor en la base de datos.
        "id": repartidor.id,

        # Datos personales del repartidor.
        "nombre": repartidor.nombre,
        "apellido": repartidor.apellido,
        "dni": repartidor.dni,
        "telefono": repartidor.telefono,
        "mail": repartidor.mail,

        # Información relacionada con su función de reparto.
        "tipo_vehiculo": repartidor.tipo_vehiculo,
        "estado": Repartidor.Estado.ACTIVO,

        # Lista con los IDs de los paquetes asignados al repartidor.
        "listado_id_pedidos_asignados": (
            repartidor.listado_id_pedidos_asignados
        ),
    }


def _repartidores_disponibles():
    """Queryset de repartidores con estado disponible (normaliza mayúsculas y espacios)."""
    return Repartidor.objects.annotate(
        estado_normalizado=Upper(Trim(F("estado"), output_field=CharField()))
    ).filter(estado_normalizado__in=ESTADOS_DISPONIBLES)


def _repartidores_con_vehiculo_para(paquete):
    """
    Disponibles cuyo vehículo alcanza el tamaño del paquete.

    ``tamanio_maximo_nivel`` es NULL para vehículos desconocidos, y el filtro
    ``>=`` lo descarta, así que nunca se ofrece un vehículo no reconocido.
    """
    return _repartidores_disponibles().filter(
        tamanio_maximo_nivel__gte=paquete.tamanio_nivel
    )


def _paquete_to_dict(paquete):
    """Resumen del paquete asignado para la respuesta del POST."""
    return {
        "id": paquete.id,
        "estado": paquete.estado,
        "repartidor": paquete.repartidor_id,
    }


def _buscar_paquete(pk):
    """Paquete con ese pk, o ``None`` si no existe o el pk no es válido."""
    try:
        return Paquete.objects.get(pk=pk)
    except (Paquete.DoesNotExist, ValueError, TypeError):
        return None


def _listar_para_paquete(request, paquete_pk):
    """GET con ``?paquete=``: solo disponibles con vehículo adecuado."""
    if paquete_pk in (None, ""):
        return JsonResponse({"paquete": MSG_OBLIGATORIO}, status=400)

    paquete = _buscar_paquete(paquete_pk)
    if paquete is None:
        return JsonResponse({"paquete": "Paquete inválido."}, status=400)

    if paquete.tamanio_nivel is None:
        return JsonResponse({"paquete": "Tamaño inválido."}, status=400)

    repartidores = list(_repartidores_con_vehiculo_para(paquete))

    # Escenario 2: no hay repartidores con el vehículo necesario ahora mismo.
    # El paquete queda sin asignar (pendiente) y el frontend muestra el mensaje.
    if not repartidores:
        return JsonResponse(
            {
                "mensaje": MSG_NO_HAY_CON_VEHICULO,
                "repartidores": [],
            },
            status=200,
        )

    return JsonResponse(
        {"repartidores": [_repartidor_to_dict(r) for r in repartidores]},
        status=200,
    )


def _listar_todos_disponibles():
    """GET sin ``?paquete=``: todos los disponibles, sin filtrar por vehículo."""
    repartidores = list(_repartidores_disponibles())

    # Si no hay repartidores activos, devuelve una lista vacía
    # y un mensaje informativo para el frontend.
    if not repartidores:
        return JsonResponse(
            {
                "mensaje": MSG_NO_HAY_REPARTIDORES_DISPONIBLES,
                "repartidores": [],
            },
            status=200,
        )

    return JsonResponse(
        {"repartidores": [_repartidor_to_dict(r) for r in repartidores]},
        status=200,
    )


def _asignar(request):
    """POST: el coordinador asigna directamente un repartidor a un paquete."""
    data = _parse_body(request)
    if data is None:
        return JsonResponse({"detail": "El cuerpo debe ser JSON válido."}, status=400)

    faltantes = {
        campo: MSG_OBLIGATORIO
        for campo in ("paquete", "repartidor")
        if data.get(campo) is None or str(data.get(campo)).strip() == ""
    }
    if faltantes:
        return JsonResponse(faltantes, status=400)

    with transaction.atomic():
        # select_for_update: evita que dos coordinadores asignen el mismo paquete a la vez.
        paquete = (
            Paquete.objects.select_for_update()
            .filter(pk=data["paquete"])
            .first()
        ) if _es_entero(data["paquete"]) else None
        if paquete is None:
            return JsonResponse({"detail": "Paquete no encontrado."}, status=404)

        repartidor = (
            Repartidor.objects.filter(pk=data["repartidor"]).first()
            if _es_entero(data["repartidor"])
            else None
        )
        if repartidor is None:
            return JsonResponse({"detail": "Repartidor no encontrado."}, status=404)

        if paquete.estado.strip().upper() in ESTADOS_NO_ASIGNABLES:
            return JsonResponse(
                {"detail": "El paquete ya no está en curso."}, status=409
            )
        if paquete.repartidor_id is not None:
            return JsonResponse(
                {"detail": "El paquete ya tiene un repartidor asignado."}, status=409
            )

        # Solo disponibles: se verifica contra el mismo filtro que el listado.
        if not _repartidores_disponibles().filter(pk=repartidor.pk).exists():
            return JsonResponse(
                {"repartidor": "El repartidor no está disponible."}, status=400
            )

        if paquete.tamanio_nivel is None:
            return JsonResponse({"paquete": "Tamaño inválido."}, status=400)
        if not _repartidores_con_vehiculo_para(paquete).filter(pk=repartidor.pk).exists():
            return JsonResponse({"repartidor": MSG_NO_HAY_CON_VEHICULO}, status=400)

        # Solo se cambia el repartidor. El estado del paquete lo actualiza
        # el repartidor a partir de ahora.
        paquete.repartidor = repartidor
        paquete.save(update_fields=["repartidor"])

    return JsonResponse(_paquete_to_dict(paquete), status=200)


def _es_entero(valor):
    """True si ``valor`` puede usarse como pk entero."""
    try:
        int(valor)
    except (TypeError, ValueError):
        return False
    return True


@csrf_exempt
def asignar_repartidor(request):
    """
    Lista repartidores para asignar (``GET``) o asigna uno a un paquete (``POST``).

    Ver docstring del módulo para el contrato completo.
    """
    if request.method == "GET":
        paquete_pk = request.GET.get("paquete")
        if paquete_pk is None:
            return _listar_todos_disponibles()
        return _listar_para_paquete(request, paquete_pk)

    if request.method == "POST":
        return _asignar(request)

    return JsonResponse(
        {"error": "Método no permitido."},
        status=405,
    )
