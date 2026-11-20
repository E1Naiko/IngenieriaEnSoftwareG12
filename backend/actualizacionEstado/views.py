"""Vistas para actualizar el estado de los paquetes/pedidos (HU #34, #38 y #23).

Dos caminos, con requisitos distintos:

- ``GET``: consulta pública (la usa la pantalla de seguimiento, HU #14). No
  pide credenciales y solo devuelve datos del paquete.
- ``POST``: lo usa el dashboard del **repartidor**. El backend no guarda
  sesión del repartidor, así que el ``token`` del cuerpo identifica a quien
  pide el cambio y se valida:

  * ``400`` si falta el token o el cuerpo no es JSON.
  * ``401`` si el token no corresponde a ningún repartidor.
  * ``403`` si el repartidor está **dado de baja** (HU #38): en el front el
    dashboard cierra la sesión, pero un request directo tiene que rechazarse
    igual.
  * ``403`` si intenta modificar un paquete que **no tiene asignado**. El
    historial y la lista de pedidos del repartidor se arman con la FK
    ``paquete.repartidor``, así que sin esta verificación cualquiera con un
    token podía cambiar el estado de un paquete ajeno.

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
import re

from django.core.files.base import ContentFile
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.estados import es_baja
from core.models import Comprobante, Paquete, Repartidor
from crudComercios.views import _parse_body
from verPedidosPorAsignar.services import (
    DESTINOS_CANCELACION,
    CancelacionInvalida,
    registrar_cancelacion,
)

MSG_TOKEN_FALTANTE = "Falta el token"
MSG_TOKEN_INVALIDO = "Token inválido"
MSG_REPARTIDOR_BAJA = (
    "El repartidor no se encuentra habilitado. Comuníquese con el coordinador"
)
MSG_PAQUETE_AJENO = "El paquete no está asignado a este repartidor"

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


def error(mensaje, status=400):
    return JsonResponse({"message": mensaje}, status=status)


@csrf_exempt  # Las escrituras se autentican con el token del repartidor, no con cookies.
@require_http_methods(["GET", "POST"])
def cambiar_estado_pedido(request):
    """
    GET /api/cambiar-estado-pedido/
        Lista todos los paquetes existentes.
        Opcional: ?cod_seguimiento=SRFR-XXXX para filtrar por uno específico.

    POST /api/cambiar-estado-pedido/
        Actualiza el estado de un paquete específico.
        Body JSON esperado: {"token": "...", "id": <id_paquete>, "estado": ...}
        Para ``entregado`` además: {"dni_receptor": "<dni del cliente>", "foto_dni": "data:image/...;base64,..." (opcional)}
    """

    # --- GET: Listar paquetes ---
    if request.method == "GET":
        paquetes = Paquete.objects.select_related("repartidor")
        if codigo := request.GET.get("cod_seguimiento"):
            paquetes = paquetes.filter(cod_seguimiento=codigo)
        lista = [to_dict(p) for p in paquetes]
        mensaje = "Paquetes obtenidos correctamente." if lista else "No hay paquetes registrados."
        return JsonResponse({"message": mensaje, "paquetes": lista})

    # --- POST: Actualizar estado de un paquete ---
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

    # Quién pide el cambio: el token del repartidor que tiene la sesión abierta
    # en el dashboard. Se normaliza como en loginRepartidor.
    if "token" not in data or data.get("token") is None:
        return error(MSG_TOKEN_FALTANTE, 400)
    token = str(data.get("token") or "").strip().upper()
    if not token:
        # La clave vino vacía: equivale a un token que no identifica a nadie.
        return JsonResponse({"message": MSG_TOKEN_INVALIDO}, status=401)
    repartidor, error_auth = _repartidor_por_token(token)
    if error_auth is not None:
        return error_auth

    with transaction.atomic():
        paquete = Paquete.objects.select_for_update().filter(pk=paquete_id).first()
        if paquete is None:
            return error(f"No se encontró un paquete con id={paquete_id}.", 404)
        # Solo el repartidor asignado puede cambiar el estado de su paquete.
        if not _paquete_del_repartidor(paquete, repartidor):
            return error(MSG_PAQUETE_AJENO, 403)

        estado = paquete.estado.strip().lower()
        if estado in Paquete.ESTADOS_CERRADOS:
            return error(f"No se puede modificar el estado de un paquete '{paquete.estado}'.")

        confirmando_devolucion = (
            estado == Paquete.Estado.EN_DEVOLUCION
            and nuevo_estado == Paquete.Estado.CANCELADO
            and "causa" not in data
        )
        if nuevo_estado in DESTINOS_CANCELACION and not confirmando_devolucion:
            # Cancelación desde el desplegable del dashboard (HU #35).
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
        if nuevo_estado != siguiente.get(estado) and nuevo_estado != estado:
            return error("No se puede modificar el pedido a ese estado.", 409)

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

        paquete.estado = nuevo_estado
        campos = ["estado"]
        if nuevo_estado == Paquete.Estado.ENTREGADO:
            campos.append("comprobante")
        if nuevo_estado == Paquete.Estado.ENTREGADO or confirmando_devolucion:
            paquete.retiro_latitud = paquete.retiro_longitud = None
            campos += ["retiro_latitud", "retiro_longitud"]
        paquete.save(update_fields=campos)

        if confirmando_devolucion:
            mensaje = "Devolución al comercio confirmada."
        elif nuevo_estado == Paquete.Estado.ENTREGADO:
            mensaje = "Entrega validada con el DNI del receptor."
        else:
            mensaje = "Estado del paquete actualizado correctamente."
        return JsonResponse({"message": mensaje, "paquete": to_dict(paquete)})
