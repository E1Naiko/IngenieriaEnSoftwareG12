"""Disponibilidad del repartidor (disponible / no disponible)."""

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.models import Repartidor

# Mensajes. Ajustar el de éxito al texto exacto de la historia de usuario.
MSG_DISPONIBLE = "Ahora estás disponible para recibir pedidos"
MSG_NO_DISPONIBLE = "Ahora no estás disponible para recibir pedidos"
MSG_JSON_INVALIDO = "El cuerpo debe ser JSON válido."
MSG_FALTA_TOKEN = "Falta el token"
MSG_TOKEN_INVALIDO = "Token inválido"
MSG_ESTADO_INVALIDO = "Estado inválido"
MSG_REPARTIDOR_BAJA = (
    "El repartidor no se encuentra habilitado. Comuníquese con el coordinador"
)

# Estados que el repartidor puede elegir, y el valor que se guarda en el modelo.
# Las claves están normalizadas: minúscula y con espacios.
ESTADOS_PERMITIDOS = {
    "disponible": Repartidor.Estado.ACTIVO,
    "no disponible": Repartidor.Estado.INACTIVO,
    # Los valores del modelo también se aceptan.
    "activo": Repartidor.Estado.ACTIVO,
    "inactivo": Repartidor.Estado.INACTIVO,
}

# Valores de Repartidor.estado que cuentan como "disponible", en minúscula.
# "disponible" es un valor que hay en la base de desarrollo además de ACTIVO.
ESTADOS_DISPONIBLES = {"activo", "disponible"}


def _estado_to_dict(repartidor):
    """Estado actual del repartidor, ya resuelto para el front.

    Evita que el front tenga que interpretar los distintos valores
    que hay guardados (ACTIVO, DISPONIBLE, inactivo...).
    """
    disponible = repartidor.estado.strip().lower() in ESTADOS_DISPONIBLES
    return {
        "estado": "activo" if disponible else "inactivo",
        "disponible": disponible,
    }


@csrf_exempt  # El front del repartidor no maneja token CSRF.
@require_http_methods(["GET", "POST"])  # Los demás métodos reciben 405.
def cambiar_disponibilidad(request):
    """/api/disponibilidad-repartidor/ — consulta y cambio de disponibilidad.

    GET  ?token=A7K2Q9                              → estado actual.
    POST {"token": "A7K2Q9", "estado": "disponible" | "no_disponible"}
                                                    → cambia el estado.

    Devuelve:
        200: {"estado": "activo" | "inactivo", "disponible": true | false}
             (el POST agrega "message").
        400: JSON inválido, falta el token o el estado no es válido.
        403: El repartidor está dado de baja.
        404: El token no corresponde a ningún repartidor.
    """
    if request.method == "GET":
        # En la consulta el token llega en la URL.
        token = str(request.GET.get("token") or "").strip().upper()
    else:
        # En el cambio el token llega en el cuerpo, como JSON.
        try:
            data = json.loads(request.body or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = None
        if not isinstance(data, dict):
            return JsonResponse({"message": MSG_JSON_INVALIDO}, status=400)
        token = str(data.get("token") or "").strip().upper()

    # El token identifica al repartidor (igual que en pedidosAsignados).
    if not token:
        return JsonResponse({"message": MSG_FALTA_TOKEN}, status=400)

    repartidor = Repartidor.objects.filter(token=token).first()
    if repartidor is None:
        return JsonResponse({"message": MSG_TOKEN_INVALIDO}, status=404)

    # Un repartidor dado de baja no puede consultar ni cambiar su estado.
    if repartidor.estado.strip().lower() == "baja":
        return JsonResponse({"message": MSG_REPARTIDOR_BAJA}, status=403)

    if request.method == "GET":
        return JsonResponse(_estado_to_dict(repartidor))

    # --- POST: valida el estado pedido (sin distinguir mayúsculas) ---
    # Se normaliza: minúsculas, sin espacios de más y "_" como espacio
    # (así "No_Disponible" y "no disponible" valen lo mismo).
    pedido = " ".join(str(data.get("estado") or "").replace("_", " ").lower().split())
    nuevo_estado = ESTADOS_PERMITIDOS.get(pedido)
    if nuevo_estado is None:
        return JsonResponse({"estado": MSG_ESTADO_INVALIDO}, status=400)

    # Guarda solo el campo estado, para no pisar otros datos.
    repartidor.estado = nuevo_estado
    repartidor.save(update_fields=["estado"])

    # El mensaje depende del estado al que pasó.
    if nuevo_estado == Repartidor.Estado.ACTIVO:
        mensaje = MSG_DISPONIBLE
    else:
        mensaje = MSG_NO_DISPONIBLE

    return JsonResponse({"message": mensaje, **_estado_to_dict(repartidor)})