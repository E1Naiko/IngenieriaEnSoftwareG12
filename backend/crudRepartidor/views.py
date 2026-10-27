from django.shortcuts import render
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.models import Repartidor

# Create your views here.
def _parse_body(request):
    """Decodifica el body como JSON y lo valida.

    Args:
        request: ``HttpRequest`` de Django.

    Returns:
        dict: diccionario del body si es JSON válido.
        dict vacío ``{}`` si el body está vacío (útil para que la validación
        posterior reporte campos faltantes en vez de un 400 genérico).
        None si el body no es JSON válido (``JSONDecodeError``/``UnicodeDecodeError``)
        o si el JSON no es un objeto (lista, número, etc.).
    """
    if not request.body:
        return {}
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data



def _repartidor_to_dict(repartidor):
    """Serializa un ``repartidor`` al contrato JSON de la API.

    Args:
        repartidor: instancia ``core.models.repartidor`` (guardada o no).

    Returns:
        dict con .
    """
    return {
        "id": repartidor.id,
        "nombre": repartidor.nombre,
        "apellido": repartidor.apellido,
        "dni": repartidor.dni,
        "telefono": repartidor.telefono,
        "mail": repartidor.mail,
        "tipo_vehiculo": repartidor.tipo_vehiculo,
        "estado": repartidor.estado,
        "token": repartidor.token,
       
    }