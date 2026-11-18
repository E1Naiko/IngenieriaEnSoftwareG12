"""Cambio de disponibilidad del repartidor (Activo / Inactivo)."""

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.models import Repartidor

# Mensajes. Ajustar el de éxito al texto exacto de la historia de usuario.
MSG_DISPONIBLE = "Ahora estás disponible para recibir pedidos"
MSG_NO_DISPONIBLE = "Ahora no estas disponible para recibir pedidos"
MSG_JSON_INVALIDO = "El cuerpo debe ser JSON válido."
MSG_FALTA_TOKEN = "Falta el token"
MSG_TOKEN_INVALIDO = "Token inválido"
MSG_ESTADO_INVALIDO = "Estado inválido"
MSG_REPARTIDOR_BAJA = (
    "El repartidor no se encuentra habilitado. Comuníquese con el coordinador"
)

# Estados que el repartidor puede elegir, y el valor que se guarda en el modelo.
# Las claves están en minúscula: lo que llega se normaliza antes de buscar.
ESTADOS_PERMITIDOS = {
    "disponible": Repartidor.Estado.ACTIVO,
    "no disponible": Repartidor.Estado.INACTIVO,
    # Los valores del modelo también se aceptan.
    "activo": Repartidor.Estado.ACTIVO,
    "inactivo": Repartidor.Estado.INACTIVO,
}

@csrf_exempt  # El front del repartidor no maneja token CSRF.
@require_POST  # Acepta únicamente POST; los demás métodos reciben 405.
def cambiar_disponibilidad(request):
    """POST /api/disponibilidad-repartidor/ — el repartidor cambia su estado.

    Body: {"token": "A7K2Q9", "estado": "activo" | "inactivo"}

    Devuelve:
        200: Estado actualizado (también si ya tenía ese estado).
        400: JSON inválido, falta el token o el estado no es válido.
        403: El repartidor está dado de baja.
        404: El token no corresponde a ningún repartidor.
    """
    # Lee el cuerpo como JSON; tiene que ser un objeto.
    try:
        data = json.loads(request.body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = None
    if not isinstance(data, dict):
        return JsonResponse({"message": MSG_JSON_INVALIDO}, status=400)

    # El token identifica al repartidor (igual que en pedidosAsignados).
    token = str(data.get("token") or "").strip().upper()
    if not token:
        return JsonResponse({"message": MSG_FALTA_TOKEN}, status=400)

    repartidor = Repartidor.objects.filter(token=token).first()
    if repartidor is None:
        return JsonResponse({"message": MSG_TOKEN_INVALIDO}, status=404)

    # Un repartidor dado de baja no puede cambiar su disponibilidad.
    if repartidor.estado.strip().lower() == "baja":
        return JsonResponse({"message": MSG_REPARTIDOR_BAJA}, status=403)

    # Valida el estado pedido (sin distinguir mayúsculas de minúsculas).
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

    return JsonResponse({"message": mensaje, "estado": repartidor.estado})