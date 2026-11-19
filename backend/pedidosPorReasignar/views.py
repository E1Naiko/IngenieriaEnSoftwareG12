"""
Pedidos "Por Reasignar" (HU #36).

Rutas (prefijo global ``/api/`` en ``config/urls.py``)::

    POST /api/pedidos-por-reasignar/                 body {"token": "ABC123"}
    POST /api/pedidos-por-reasignar/aceptar/<id>/   body {"token": "ABC123"}

**Sin estado nuevo y sin campos nuevos.** La lista son los paquetes en estado
``cancelado``: es lo que deja el botón "Confirmar cancelación" del dashboard
del repartidor (``POST /api/cambiar-estado-pedido/`` con ``estado:
"cancelado"``), que además **no limpia** ``paquete.repartidor``. Por eso la
"última persona que retiró el paquete" se lee directamente de esa FK, con su
nombre y apellido, sin agregar una tabla de historial ni un snapshot.

Reglas que implementa este módulo:

- El repartidor se identifica con su token único en CADA request (el backend
  no guarda sesión: el front tiene el token en ``localStorage``) y debe estar
  operativo (``ACTIVO`` en este esquema; se toleran los valores legados
  ``DISPONIBLE``/``OPERATIVO``).
- La lista son TODOS los ``cancelado``: no hay filtro por zona cercana
  (quedó descartado) ni límite de pedidos asignados.
- Cada ítem muestra solo lo necesario para decidir: dirección de retiro,
  dirección de destino, tamaño y el nombre y apellido del último repartidor
  que tuvo el paquete (``ultimo_repartidor``, ``null`` si nunca tuvo uno).
- "El primero que lo toma se lo queda": aceptar es un ``UPDATE`` condicional
  dentro de una transacción, con ``estado=cancelado`` en el ``WHERE``. Si dos
  repartidores aceptan a la vez, el segundo actualiza 0 filas y recibe 409;
  el pedido deja de estar ``cancelado`` y desaparece de la lista de todos.
- Al aceptar, el paquete pasa a ``asignado`` y la FK ``repartidor`` pasa a
  apuntar al nuevo repartidor: con eso ya aparece en
  ``/api/paquetes-repartidor/`` (HU #17) sin mantener listas duplicadas.

Respuestas del listado::

    200 → {"pedidos": [...]}                                (escenario 1)
    200 → {"mensaje": "No hay pedidos...", "pedidos": []}   (escenario 2)
    400 → body no JSON válido / falta el token
    404 → {"message": "Sesión inválida"}   (token inexistente)
    403 → {"message": "..."}               (repartidor inactivo o de baja)
    405 → método no permitido
"""

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.models import Paquete, Repartidor
from crudComercios.views import _parse_body

# El botón "Confirmar cancelación" del dashboard publica el pedido acá.
# ``iexact`` porque la base de desarrollo tiene estados en mayúsculas
# (ver tests de pedidosAsignados y la migración 0009).
ESTADO_PUBLICADO = Paquete.Estado.CANCELADO

# "Operativo" = ACTIVO (Repartidor.Estado, migración 0009). Los otros dos
# valores son equivalentes históricos que pueden existir en datos de dev.
ESTADOS_OPERATIVOS = {"ACTIVO", "DISPONIBLE", "OPERATIVO"}

MSG_SIN_PEDIDOS = "No hay pedidos pendientes de reasignación."
MSG_SESION_INVALIDA = "Sesión inválida"
MSG_NO_OPERATIVO = "El repartidor no está operativo"
MSG_NO_ENCONTRADO = "No se encontró el pedido."
MSG_YA_TOMADO = "El pedido ya fue tomado por otro repartidor."


def _autorizar(request):
    """Devuelve ``(repartidor, None)`` o ``(None, JsonResponse de error)``."""
    data = _parse_body(request)
    if data is None:
        return None, JsonResponse(
            {"message": "El cuerpo debe ser JSON válido."}, status=400
        )

    token = str(data.get("token") or "").strip().upper()
    if not token:
        return None, JsonResponse({"message": "Falta el token"}, status=400)

    repartidor = Repartidor.objects.filter(token=token).first()
    if repartidor is None:
        return None, JsonResponse({"message": MSG_SESION_INVALIDA}, status=404)

    if (repartidor.estado or "").strip().upper() not in ESTADOS_OPERATIVOS:
        return None, JsonResponse({"message": MSG_NO_OPERATIVO}, status=403)

    return repartidor, None


def _publicados():
    """La lista: pedidos cancelados, con el último repartidor a mano."""
    return (
        Paquete.objects.filter(estado__iexact=ESTADO_PUBLICADO)
        .select_related("cliente", "comercio", "repartidor")
        .order_by("-id")
    )


def _pedido_to_dict(paquete):
    """Contrato JSON: lo necesario para decidir + quién lo tuvo por última vez."""
    anterior = paquete.repartidor
    return {
        "id": paquete.id,
        "direccion_retiro": paquete.comercio.direccion,
        "direccion_destino": paquete.cliente.direccion,
        "tamanio": paquete.tamanio,
        "ultimo_repartidor": (
            {"nombre": anterior.nombre, "apellido": anterior.apellido}
            if anterior
            else None
        ),
    }


@csrf_exempt  # el front del repartidor no maneja token CSRF
@require_POST
def listar(request):
    """Lista de pedidos publicados para reasignación (escenarios 1 y 2)."""
    _, error = _autorizar(request)
    if error is not None:
        return error

    pedidos = [_pedido_to_dict(p) for p in _publicados()]
    if not pedidos:
        return JsonResponse({"mensaje": MSG_SIN_PEDIDOS, "pedidos": []})
    return JsonResponse({"pedidos": pedidos})


@csrf_exempt
@require_POST
def aceptar(request, pk):
    """Toma el pedido. Solo el primer repartidor en llegar se lo queda."""
    repartidor, error = _autorizar(request)
    if error is not None:
        return error

    with transaction.atomic():
        # El WHERE es la condición de carrera: en PostgreSQL la segunda
        # transacción espera a la primera y reevalúa el estado ya cambiado,
        # por lo que actualiza 0 filas. No hace falta select_for_update ni
        # leer antes de escribir, y también es atómico en SQLite (tests).
        # La FK ``repartidor`` se sobreescribe con quien acepta: deja de ser
        # el "último que lo tuvo" y pasa a ser el asignado actual.
        filas = (
            Paquete.objects.filter(pk=pk, estado__iexact=ESTADO_PUBLICADO)
            .update(repartidor=repartidor, estado=Paquete.Estado.ASIGNADO)
        )

    if filas == 0:
        if not Paquete.objects.filter(pk=pk).exists():
            return JsonResponse({"message": MSG_NO_ENCONTRADO}, status=404)
        return JsonResponse({"message": MSG_YA_TOMADO}, status=409)

    # No se devuelve el contrato de la lista: después de aceptar, la FK ya
    # apunta al nuevo repartidor, así que ``ultimo_repartidor`` no tendría
    # sentido. El front igual refresca la lista al recibir el 200.
    return JsonResponse(
        {
            "message": "Pedido aceptado",
            "pedido": {"id": pk, "estado": Paquete.Estado.ASIGNADO},
        }
    )
