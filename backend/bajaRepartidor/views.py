"""Vistas de la HU #38: baja lógica de un repartidor.

Modelo de autenticación (igual que el resto de las acciones del coordinador,
por ejemplo el PUT de edición de la HU #39 en ``crudRepartidor``):

- Hay una sola persona con el rol de coordinador, así que alcanza con que haya
  una sesión de Django iniciada (``request.user.is_authenticated``).
- Las vistas son ``@csrf_exempt``. No es un descuido: el front llama por rutas
  relativas y en el despliegue el pedido llega proxificado (rewrite de Vercel
  hacia Render, túnel de desarrollo, preview del sandbox). En esos casos el
  header ``Origin`` del navegador no coincide con el host que ve Django y la
  verificación CSRF de Django devuelve 403 aunque el token sea correcto.
  Por eso todas las acciones del coordinador en este proyecto son
  ``@csrf_exempt`` (ver ``crudComercios/README.md``, sección 9).
- El riesgo que cubre CSRF queda acotado por ``SESSION_COOKIE_SAMESITE="Lax"``:
  un POST desde otro sitio no lleva la cookie de sesión.

Si algún día se habilita CSRF (por ejemplo, sirviendo el front y la API desde
el mismo dominio), quitar los ``@csrf_exempt``, agregar el dominio del front a
``CSRF_TRUSTED_ORIGINS`` y el front ya está listo: ``utils/csrf.ts`` manda
``X-CSRFToken`` en todas las peticiones que modifican datos.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from core.estados import es_baja
from core.models import Repartidor

MSG_NO_ENCONTRADO = "Repartidor no encontrado"
MSG_YA_DE_BAJA = "El repartidor ya fue dado de baja"
MSG_NO_AUTENTICADO = "No autenticado"
MSG_BAJA_EXITOSA = "Repartidor dado de baja con éxito"


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
    """GET /api/repartidores/<id>/detalle-baja/ — datos para el modal.

    Devuelve:
        200: datos del repartidor.
        400: ya está dado de baja (no tiene sentido pedir confirmación).
        401: no hay sesión de coordinador.
        404: el repartidor no existe.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": MSG_NO_AUTENTICADO}, status=401)

    try:
        repartidor = Repartidor.objects.get(pk=repartidor_id)
    except Repartidor.DoesNotExist:
        return JsonResponse({"error": MSG_NO_ENCONTRADO}, status=404)

    if es_baja(repartidor.estado):
        return JsonResponse({"error": MSG_YA_DE_BAJA}, status=400)

    return JsonResponse({"repartidor": _repartidor_to_dict(repartidor)}, status=200)


@csrf_exempt  # Ver el docstring del módulo: el pedido llega proxificado.
@require_http_methods(["POST", "PATCH", "DELETE"])
def repartidor_baja(request, repartidor_id):
    """POST /api/repartidores/<id>/baja/ — baja lógica (estado='baja').

    Devuelve:
        200: baja aplicada; incluye el mensaje y el repartidor actualizado.
        400: ya estaba dado de baja.
        401: no hay sesión de coordinador.
        404: el repartidor no existe.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": MSG_NO_AUTENTICADO}, status=401)

    try:
        repartidor = Repartidor.objects.get(pk=repartidor_id)
    except Repartidor.DoesNotExist:
        return JsonResponse({"error": MSG_NO_ENCONTRADO}, status=404)

    if es_baja(repartidor.estado):
        return JsonResponse({"error": MSG_YA_DE_BAJA}, status=400)

    # .update() cambia solo el estado: no dispara Repartidor.save() (que
    # generaría un token nuevo). La baja es lógica, el token se conserva y el
    # login del repartidor lo rechaza por el estado.
    Repartidor.objects.filter(pk=repartidor_id).update(estado=Repartidor.Estado.BAJA)
    repartidor.refresh_from_db()

    return JsonResponse(
        {
            "mensaje": MSG_BAJA_EXITOSA,
            "repartidor": _repartidor_to_dict(repartidor),
        },
        status=200,
    )
