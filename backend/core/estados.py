"""Reglas compartidas sobre el estado del repartidor.

El esquema guarda ``repartidor.estado`` como ``varchar(255)`` y en la base
conviven valores de distintas épocas: ``ACTIVO``, ``activo``, ``DISPONIBLE``,
``inactivo``, ``baja`` y ``BAJA``. Cada app comparaba el estado a su manera y
la baja se colaba en las comparaciones exactas: un repartidor con
``estado='BAJA'`` podía seguir iniciando sesión porque ``loginRepartidor``
comparaba contra el literal ``"baja"``.

Estas funciones son el único punto donde se decide "este repartidor está dado
de baja". Toda app que tenga que bloquear a un repartidor dado de baja debe
usarlas en lugar de comparar el string a mano.
"""

from core.models import Repartidor


def es_baja(estado) -> bool:
    """True si el estado guardado representa una baja.

    No distingue mayúsculas, y tolera espacios al principio o al final:
    ``"baja"``, ``"BAJA"`` y ``" Baja "`` son la misma cosa.
    """
    return str(estado or "").strip().lower() == Repartidor.Estado.BAJA.lower()


def esta_habilitado(repartidor) -> bool:
    """True si el repartidor puede operar (iniciar sesión, cambiar estados...).

    Un repartidor dado de baja no está habilitado, sin importar el estado de
    disponibilidad que tuviera antes (``ACTIVO``/``DISPONIBLE``).
    """
    return repartidor is not None and not es_baja(repartidor.estado)
