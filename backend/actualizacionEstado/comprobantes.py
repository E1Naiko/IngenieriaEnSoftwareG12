"""Guarda la foto del DNI que acredita la entrega de un paquete.

El frontend del repartidor manda la imagen como *data URL* base64 dentro del
JSON (``{"foto_dni": "data:image/jpeg;base64,..."}``), porque el endpoint
``/api/cambiar-estado-pedido/`` solo habla JSON. Acá se valida y se guarda
como ``core.models.Comprobante`` (columna ``file``, ``varchar(255)`` con
``upload_to="comprobantes/%Y/%m/"``): es el uno a uno que el diagrama tiene
previsto para eso, ``paquete.id_comprobante``.

Reglas:

- Formatos aceptados: JPEG, PNG y WebP (lo que saca la cámara del celular).
  Se verifica la firma binaria, no la cabecera de la data URL.
- Tamaño máximo: ``COMPROBANTE_MAX_BYTES`` sobre el archivo real (el base64
  pesa ~33 % más).
- La foto es opcional para la API: si el paquete se marca entregado sin foto,
  el estado cambia igual y el paquete queda sin comprobante.
"""

import base64
import binascii
import re

from django.core.files.base import ContentFile

from core.models import Comprobante

COMPROBANTE_MAX_BYTES = 5 * 1024 * 1024

# Cabecera de una data URL de imagen: "data:image/png;base64,...."
_DATA_URL = re.compile(
    r"^data:image/(?P<tipo>jpeg|jpg|png|webp);base64,(?P<datos>.+)$", re.DOTALL | re.IGNORECASE
)
_EXTENSIONES = {"jpeg": "jpg", "jpg": "jpg", "png": "png", "webp": "webp"}


class FotoInvalida(Exception):
    """La foto del DNI no se puede guardar; el mensaje es apto para mostrar."""


def _detectar_formato(contenido):
    """Formato real por firma binaria: ``jpg``, ``png``, ``webp`` o ``None``."""
    if contenido.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if contenido.startswith(b"RIFF") and contenido[8:12] == b"WEBP":
        return "webp"
    return None


def _decodificar(foto):
    """Devuelve ``(bytes, extensión)`` validando cabecera, base64 y tamaño."""
    if not isinstance(foto, str) or not foto.strip():
        raise FotoInvalida("La foto del DNI llegó vacía.")
    foto = foto.strip()
    if len(foto) > COMPROBANTE_MAX_BYTES * 2:  # corta antes de decodificar algo gigante
        raise FotoInvalida("La foto del DNI supera el máximo de 5 MB.")

    coincidencia = _DATA_URL.match(foto)
    try:
        if coincidencia:
            contenido = base64.b64decode(coincidencia.group("datos"), validate=True)
            esperado = _EXTENSIONES[coincidencia.group("tipo").lower()]
            if _detectar_formato(contenido) != esperado:
                raise FotoInvalida("La foto del DNI no coincide con el formato declarado.")
        else:
            # Sin cabecera: se acepta base64 pelado y el formato sale de la firma.
            contenido = base64.b64decode(foto, validate=True)
            if _detectar_formato(contenido) is None:
                raise FotoInvalida("La foto del DNI debe ser una imagen JPEG, PNG o WebP.")
    except (binascii.Error, ValueError) as exc:
        raise FotoInvalida("La foto del DNI no es un base64 válido.") from exc

    if len(contenido) > COMPROBANTE_MAX_BYTES:
        raise FotoInvalida("La foto del DNI supera el máximo de 5 MB.")
    return contenido, _detectar_formato(contenido)


def guardar_foto_dni(paquete, foto):
    """Valida ``foto`` y la adjunta al paquete como ``Comprobante``.

    No guarda el paquete: el llamador ya está dentro de la transacción que
    actualiza el estado. Deja listo ``paquete.comprobante`` y el archivo en
    ``MEDIA_ROOT``; el ``save`` del paquete incluye la columna
    ``id_comprobante``.
    """
    contenido, formato = _decodificar(foto)

    comprobante = paquete.comprobante or Comprobante.objects.create()
    comprobante.file.save(
        f"paquete-{paquete.pk}-dni.{formato}", ContentFile(contenido), save=True
    )
    paquete.comprobante = comprobante
    return comprobante
