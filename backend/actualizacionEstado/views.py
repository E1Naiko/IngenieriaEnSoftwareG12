"""Vistas para actualizar el estado de los paquetes/pedidos (HU #34 y #23).

HU #23 — Validar la entrega con el DNI del receptor
---------------------------------------------------
Para pasar un paquete a ``entregado`` el repartidor tiene que mandar
``dni_receptor`` en el mismo POST y ese número debe coincidir con el DNI del
cliente del paquete (``paquete.cliente.dni``). Si falta, responde ``400`` con
el texto exacto de la historia:

    "Necesario el numero del DNI del cliente para finalizar la entrega"

Si el número no coincide, ``400`` con un mensaje que dice cuál es el DNI
esperado: el repartidor está en la puerta y tiene el DNI en la mano, así que
lo correcto es que pueda corregirlo en el momento, no que se quede sin
entregar. Ninguno de los dos rechazos cambia el estado del paquete.

El comprobante (``foto_dni``, base64) es **opcional**: si llega, se guarda
como ``Comprobante`` asociado al paquete; si no, el paquete queda con
``comprobante = NULL``, igual que antes de esta historia. La foto nunca fue la
regla de la HU: la regla es el número del DNI.

La lectura del campo es tolerante con lo que ya manda el front: acepta
``dni_receptor`` y ``dni``, y valores como ``30111222``, ``"30.111.222"`` o
``" 30111222 "`` (se quedan solo los dígitos).
"""

import base64
import binascii
import json
import re

from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from core.models import Comprobante, Paquete

# Texto exacto del escenario 2 de la HU #23.
MSG_DNI_REQUERIDO = (
    "Necesario el numero del DNI del cliente para finalizar la entrega"
)
# Escenario 1 (el número no coincide). Se informa el esperado a propósito: el
# repartidor está frente al cliente y tiene que poder corregirlo.
MSG_DNI_INCORRECTO = (
    "El DNI ingresado no coincide con el del cliente del pedido. "
    "El DNI del cliente es {dni}."
)

# Tamaño máximo del comprobante en base64 (~5 MB de imagen).
MAX_FOTO_BYTES = 5 * 1024 * 1024
EXTENSIONES_FOTO = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def _solo_digitos(valor):
    """``"30.111.222"``, ``" 30 111 222 "`` → ``"30111222"``. None si no hay dígitos."""
    if valor is None or isinstance(valor, bool):
        return None
    digitos = re.sub(r"\D", "", str(valor))
    return digitos or None


def _dni_del_cuerpo(data):
    """DNI que mandó el repartidor, como texto de dígitos (o None si no vino)."""
    for clave in ("dni_receptor", "dni"):
        if clave in data:
            return _solo_digitos(data.get(clave))
    return None


def _guardar_foto(paquete, foto):
    """Asocia la foto del DNI (data URL base64) al paquete, si es válida.

    Devuelve ``None`` si se guardó o no había nada que guardar, o un
    ``JsonResponse`` de error si el contenido no es una imagen válida. La foto
    es opcional: no bloquea la entrega, pero si viene mal formada se avisa en
    vez de descartarla en silencio (era el comportamiento anterior).
    """
    if not foto:
        return None
    if not isinstance(foto, str):
        return JsonResponse({"foto_dni": "La foto del DNI no es válida."}, status=400)

    # Formatos aceptados: data:image/...;base64,XXXX o el base64 pelado.
    tipo = "image/jpeg"
    contenido = foto
    if foto.startswith("data:"):
        encabezado, _, contenido = foto.partition(",")
        tipo = encabezado[5:].split(";")[0] or tipo
    if tipo not in EXTENSIONES_FOTO:
        return JsonResponse(
            {"foto_dni": "Formato de imagen no admitido (JPEG, PNG o WebP)."},
            status=400,
        )
    try:
        bytes_foto = base64.b64decode(contenido, validate=True)
    except (binascii.Error, ValueError):
        return JsonResponse({"foto_dni": "La foto del DNI no es válida."}, status=400)
    if not bytes_foto:
        return JsonResponse({"foto_dni": "La foto del DNI está vacía."}, status=400)
    if len(bytes_foto) > MAX_FOTO_BYTES:
        return JsonResponse({"foto_dni": "La foto del DNI supera los 5 MB."}, status=400)

    comprobante = paquete.comprobante or Comprobante()
    nombre = f"dni-{paquete.cod_seguimiento}.{EXTENSIONES_FOTO[tipo]}"
    comprobante.file.save(nombre, ContentFile(bytes_foto), save=True)
    paquete.comprobante = comprobante
    return None


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


@csrf_exempt
@require_http_methods(["GET", "POST"])
def cambiar_estado_pedido(request):
    """
    GET /api/cambiar-estado-pedido/
        Lista todos los paquetes existentes.
        Opcional: ?cod_seguimiento=SRFR-XXXX para filtrar por uno específico.

    POST /api/cambiar-estado-pedido/
        Actualiza el estado de un paquete específico.
        Body JSON esperado: {"id": <id_paquete>, "estado": cualquier valor de Paquete.Estado}
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
    if request.method == "POST":
        # Parsear JSON
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"message": "El cuerpo debe ser JSON válido."}, status=400)

        if not isinstance(data, dict):
            return JsonResponse({"message": "El cuerpo debe ser un objeto JSON."}, status=400)

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

        # Validación extra: no se puede modificar un paquete ya entregado o cancelado
        if paquete.estado in [Paquete.Estado.ENTREGADO, Paquete.Estado.CANCELADO]:
            return JsonResponse(
                {"message": f"No se puede modificar el estado de un paquete '{paquete.estado}'."},
                status=400
            )

        # --- HU #23: la entrega se valida con el DNI del receptor ---
        # El paquete NO cambia de estado si falta el DNI o si no coincide.
        if nuevo_estado == Paquete.Estado.ENTREGADO:
            dni_receptor = _dni_del_cuerpo(data)
            if dni_receptor is None:
                return JsonResponse({"message": MSG_DNI_REQUERIDO}, status=400)

            dni_cliente = str(paquete.cliente.dni)
            if dni_receptor != dni_cliente:
                return JsonResponse(
                    {"message": MSG_DNI_INCORRECTO.format(dni=dni_cliente)},
                    status=400,
                )

            error_foto = _guardar_foto(paquete, data.get("foto_dni"))
            if error_foto is not None:
                return error_foto

            # `paquete` viene de un queryset sin select_related: se guardan el
            # estado y la FK del comprobante juntos.
            paquete.estado = nuevo_estado
            paquete.save(update_fields=["estado", "comprobante"])
            return JsonResponse(
                {
                    "message": "Entrega validada con el DNI del receptor.",
                    "paquete": to_dict(paquete),
                },
                status=200,
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