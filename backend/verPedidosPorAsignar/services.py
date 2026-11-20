"""Publicación, elegibilidad y toma de pedidos pendientes de reasignación."""

from datetime import timedelta
from math import asin, cos, radians, sin, sqrt

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Lower, Trim
from django.utils import timezone

from core.models import Paquete, Repartidor

ESTADOS_DISPONIBLES = {Repartidor.Estado.ACTIVO.upper(), "DISPONIBLE"}
ESTADOS_CANCELABLES = {Paquete.Estado.ASIGNADO, Paquete.Estado.RETIRADO, Paquete.Estado.EN_CAMINO}

# El desplegable envía el estado, sin distinguir ausencia y rechazo.
DESTINOS_CANCELACION = {
    Paquete.Estado.PENDIENTE_REASIGNACION: Paquete.CausaCancelacion.FUERZA_MAYOR,
    Paquete.Estado.EN_DEVOLUCION: "",
    Paquete.Estado.CANCELADO: "",
}


def ubicacion_valida(ubicacion):
    if not isinstance(ubicacion, dict):
        return None
    lat, lon = ubicacion.get("latitud"), ubicacion.get("longitud")
    if (
        type(lat) not in (int, float) or type(lon) not in (int, float)
        or not (-90 <= lat <= 90 and -180 <= lon <= 180)
    ):
        return None
    return lat, lon


def distancia_km(origen, destino):
    lat, lon = map(radians, origen)
    otra_lat, otra_lon = map(radians, destino)
    a = sin((otra_lat - lat) / 2) ** 2 + cos(lat) * cos(otra_lat) * sin((otra_lon - lon) / 2) ** 2
    return 12742 * asin(sqrt(min(1, a)))


def es_reasignacion(paquete):
    return paquete.estado.strip().lower() == Paquete.Estado.PENDIENTE_REASIGNACION


def en_oferta(paquete, ahora):
    return (
        es_reasignacion(paquete)
        and paquete.repartidor_id is None
        and paquete.reasignacion_hasta is not None
        and paquete.reasignacion_hasta > ahora
        and paquete.retiro_latitud is not None
        and paquete.retiro_longitud is not None
    )


def distancia_oferta(paquete, repartidor, ubicacion, ahora):
    """Distancia si el repartidor puede tomar la oferta; None si no es elegible."""
    capacidad = repartidor.tamanio_maximo_nivel
    if (
        not en_oferta(paquete, ahora)
        or paquete.repartidor_original_id == repartidor.pk
        or repartidor.estado.strip().upper() not in ESTADOS_DISPONIBLES
        or capacidad is None or paquete.tamanio_nivel is None
        or capacidad < paquete.tamanio_nivel
    ):
        return None
    distancia = distancia_km(ubicacion, (paquete.retiro_latitud, paquete.retiro_longitud))
    return distancia if distancia <= settings.REASIGNACION_RADIO_KM else None


class CancelacionInvalida(Exception):
    """Rechazo con un motivo que el frontend puede usar para guiar al usuario.

    ``campo`` nombra el campo culpable (``"causa"``, ``"motivo"``,
    ``"ubicacion"``) para que el cliente resalte justo ese dato en vez de
    mostrar un error genérico; ``estado_incompatible`` marca los rechazos que
    dependen del estado actual del paquete (409).
    """

    def __init__(self, mensaje, *, estado_incompatible=False, campo=None):
        super().__init__(mensaje)
        self.estado_incompatible = estado_incompatible
        self.campo = campo


def registrar_cancelacion(paquete, *, motivo, ubicacion_informada, causa=None, destino=None):
    """Registra la cancelación de un paquete bloqueado y autorizado por el llamador."""
    if paquete.estado.strip().lower() not in ESTADOS_CANCELABLES:
        raise CancelacionInvalida("El pedido no está en condiciones de ser cancelado.", estado_incompatible=True)

    if destino is None:
        # Contrato anterior: la causa explícita determina el estado final.
        destinos_por_causa = {
            Paquete.CausaCancelacion.FUERZA_MAYOR: Paquete.Estado.PENDIENTE_REASIGNACION,
            Paquete.CausaCancelacion.CLIENTE_AUSENTE: Paquete.Estado.EN_DEVOLUCION,
            Paquete.CausaCancelacion.CLIENTE_RECHAZA: Paquete.Estado.CANCELADO_POR_CLIENTE,
        }
        if causa not in Paquete.CausaCancelacion.values:
            raise CancelacionInvalida(
                "Seleccioná una causa de cancelación válida "
                f"({', '.join(Paquete.CausaCancelacion.values)}).",
                campo="causa",
            )
        destino = destinos_por_causa[causa]
        if not isinstance(motivo, str) or not motivo.strip():
            raise CancelacionInvalida("Indicá el motivo de la cancelación.", campo="motivo")
    else:
        # Contrato del desplegable: el estado es explícito y el motivo es opcional.
        if causa is not None:
            raise CancelacionInvalida("Enviá la causa o elegí el estado de cancelación, no ambos.", campo="causa")
        causa = DESTINOS_CANCELACION[destino]
        if motivo is None:
            motivo = ""

    if not isinstance(motivo, str) or len(motivo.strip()) > 500 or "\x00" in motivo:
        raise CancelacionInvalida(
            "El motivo debe ser un texto de hasta 500 caracteres.", campo="motivo"
        )

    ubicacion = ubicacion_valida(ubicacion_informada)
    if ubicacion_informada is not None and ubicacion is None:
        raise CancelacionInvalida("La ubicación indicada no es válida.", campo="ubicacion")

    paquete.causa_cancelacion = causa
    paquete.motivo_cancelacion = motivo.strip()
    paquete.retiro_latitud = paquete.retiro_longitud = None
    paquete.reasignacion_hasta = None
    paquete.estado = destino
    if destino == Paquete.Estado.PENDIENTE_REASIGNACION:
        paquete.repartidor_original_id = paquete.repartidor_id
        paquete.repartidor_id = None
        ahora = timezone.now()
        # Sin un punto de retiro no podemos saber quién está cerca: pasa directo a la cola manual.
        paquete.reasignacion_hasta = ahora
        if ubicacion is not None:
            paquete.retiro_latitud, paquete.retiro_longitud = ubicacion
            paquete.reasignacion_hasta += timedelta(minutes=settings.REASIGNACION_MINUTOS)
        mensaje = (
            "El pedido se publicó en Pedidos cercanos."
            if ubicacion else "Sin ubicación de retiro: el pedido quedó disponible para el coordinador."
        )
    elif destino == Paquete.Estado.CANCELADO_POR_CLIENTE:
        # El paquete queda en manos del repartidor, que lo lleva de vuelta al
        # comercio. No hay reasignación: el destino es su origen.
        mensaje = (
            "El cliente rechazó el pedido: devolvelo al comercio. "
            "El paquete sigue a tu cargo hasta que lo entregues en el origen."
        )
    elif destino == Paquete.Estado.EN_DEVOLUCION:
        mensaje = "Devolvé el paquete al comercio y confirmá la devolución."
    else:
        mensaje = "El pedido quedó cancelado sin reasignación."

    paquete.save(update_fields=[
        "estado", "causa_cancelacion", "motivo_cancelacion", "repartidor",
        "repartidor_original", "reasignacion_hasta", "retiro_latitud", "retiro_longitud",
    ])
    return mensaje


def _pendientes_sin_repartidor():
    return Paquete.objects.alias(estado_normalizado=Lower(Trim("estado"))).filter(
        estado_normalizado=Paquete.Estado.PENDIENTE_REASIGNACION,
        repartidor__isnull=True,
    )


def _oferta_vigente(ahora):
    return Q(reasignacion_hasta__gt=ahora, retiro_latitud__isnull=False, retiro_longitud__isnull=False)


def pendientes_para_coordinador(ahora):
    """Cola manual: ofertas vencidas o sin ubicación utilizable."""
    return _pendientes_sin_repartidor().exclude(_oferta_vigente(ahora))


def ofertas_cercanas(repartidor, ubicacion, ahora):
    if repartidor.tamanio_maximo_nivel is None:
        return []
    paquetes = _pendientes_sin_repartidor().filter(
        _oferta_vigente(ahora), tamanio_nivel__lte=repartidor.tamanio_maximo_nivel,
    ).exclude(repartidor_original=repartidor)
    ofertas = []
    for paquete in paquetes:
        distancia = distancia_oferta(paquete, repartidor, ubicacion, ahora)
        if distancia is not None:
            ofertas.append((distancia, paquete))
    return sorted(ofertas, key=lambda oferta: oferta[0])


@transaction.atomic
def tomar_oferta(pk, repartidor, ubicacion):
    # Comparte el bloqueo de fila con la asignación manual y el cambio de estado.
    paquete = Paquete.objects.select_for_update().filter(pk=pk).first()
    if paquete is None or distancia_oferta(paquete, repartidor, ubicacion, timezone.now()) is None:
        return None
    paquete.repartidor = repartidor
    paquete.estado = Paquete.Estado.ASIGNADO
    paquete.reasignacion_hasta = None
    paquete.save(update_fields=["repartidor", "estado", "reasignacion_hasta"])
    return paquete
