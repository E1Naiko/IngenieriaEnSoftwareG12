from django.shortcuts import render

# Create your views here.
# Importa el módulo json para trabajar con datos en formato JSON.
import json

# Permite devolver respuestas HTTP con contenido JSON.
from django.http import JsonResponse
from django.db.models import CharField, F
from django.db.models.functions import Upper, Trim

# Importa el modelo Repartidor definido en la aplicación core.
from core.models import Repartidor


# Mensaje que se devolverá cuando no existan repartidores activos.
MSG_NO_HAY_REPARTIDORES_DISPONIBLES = (
    "No se encuentran repartidores disponibles en este momento."
)


def _repartidor_to_dict(repartidor):
    """
    Convierte un objeto Repartidor en un diccionario de Python.

    Django utiliza este diccionario para generar la respuesta JSON
    que recibirá el frontend desarrollado con React.
    """
    return {
        # Identificador único del repartidor en la base de datos.
        "id": repartidor.id,

        # Datos personales del repartidor.
        "nombre": repartidor.nombre,
        "apellido": repartidor.apellido,
        "dni": repartidor.dni,
        "telefono": repartidor.telefono,
        "mail": repartidor.mail,

        # Información relacionada con su función de reparto.
        "tipo_vehiculo": repartidor.tipo_vehiculo,
        "estado": repartidor.Estado.ACTIVO,

        # Lista con los IDs de los repartidores asignados al repartidor.
        "listado_id_pedidos_asignados": (
            repartidor.listado_id_pedidos_asignados
        ),
    }


def asignar_repartidor(request):
    """
    Endpoint que devuelve todos los repartidores activos.

    Método HTTP permitido: GET.

    Respuestas:
    - 200: consulta exitosa, con repartidores o lista vacía.
    - 405: se utilizó un método HTTP no permitido.
    """

    # Verifica que la petición HTTP sea GET.
    # Este endpoint solamente consulta información;
    # no crea, modifica ni elimina repartidores.
    if request.method != "GET":
        return JsonResponse(
            {"error": "Método no permitido."},
            status=405,
        )

    # Consulta la base de datos mediante el ORM de Django.
    # La base de producción usa "DISPONIBLE" (además del valor legado
    # "ACTIVO"). Normalizamos mayúsculas/espacios y aceptamos ambos para
    # que el contrato funcione con datos existentes y registros nuevos.
    estados_disponibles = {
        Repartidor.Estado.ACTIVO.upper(),
        "DISPONIBLE",
    }
    repartidores = (
        Repartidor.objects.annotate(
            estado_normalizado=Upper(
                Trim(F("estado"), output_field=CharField())
            )
        )
        .filter(estado_normalizado__in=estados_disponibles)
    )

    # Comprueba si la consulta devolvió algún resultado.
    # Si no hay repartidores activos, devuelve una lista vacía
    # y un mensaje informativo para el frontend.
    if not repartidores.exists():
        return JsonResponse(
            {
                "mensaje": MSG_NO_HAY_REPARTIDORES_DISPONIBLES,
                "repartidores": [],
            },
            status=200,
        )

    # Convierte cada objeto repartidor en un diccionario.
    # La comprensión de listas genera una lista de diccionarios
    # que luego podrá convertirse en JSON.
    data = [
        _repartidor_to_dict(repartidor)
        for repartidor in repartidores
    ]

    # Devuelve los datos en formato JSON con el código HTTP 200,
    # que indica que la petición se procesó correctamente.
    return JsonResponse(
        {"repartidores": data},
        status=200,
    )
