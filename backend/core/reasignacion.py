"""Reglas compartidas entre la oferta cercana y la reasignación manual."""

from math import asin, cos, radians, sin, sqrt

from django.conf import settings

from core.models import Paquete, Repartidor

ESTADOS_DISPONIBLES = {Repartidor.Estado.ACTIVO.upper(), "DISPONIBLE"}
ESTADOS_CANCELABLES = {Paquete.Estado.ASIGNADO, Paquete.Estado.RETIRADO, Paquete.Estado.EN_CAMINO}


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


def en_oferta(paquete, ahora):
    return (
        paquete.estado.strip().lower() == Paquete.Estado.PENDIENTE_REASIGNACION
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
