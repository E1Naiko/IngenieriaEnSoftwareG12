from core.models import Paquete


def paquete_to_dict(paquete):
    data = {
        "id": paquete.id,
        "cod_seguimiento": paquete.cod_seguimiento,
        "estado": paquete.estado.lower(),  # el front arma la clase CSS con este valor
        "tamanio": paquete.tamanio,
        "destinatario": f"{paquete.cliente.nombre} {paquete.cliente.apellido}".strip(),
        "direccion": paquete.cliente.direccion,
        "comercio": paquete.comercio.nombre,
        "fecha_destino": paquete.fecha_destino.isoformat(),
    }

    if paquete.estado.lower() == Paquete.Estado.EN_DEVOLUCION:
        data["direccion_comercio"] = paquete.comercio.direccion
    if paquete.retiro_latitud is not None and paquete.retiro_longitud is not None:
        data["retiro"] = {"latitud": paquete.retiro_latitud, "longitud": paquete.retiro_longitud}
    return data
