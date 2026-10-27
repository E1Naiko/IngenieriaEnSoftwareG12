# Importa el módulo json para trabajar con datos en formato JSON.
import json

# Permite devolver respuestas HTTP con contenido JSON.
from django.http import JsonResponse
from django.db.models import CharField, F
from django.db.models.functions import Upper, Trim

# Importa el modelo Paquete definido en la aplicación core.
from core.models import Paquete
# Create your views here.

# Mensaje que se devolverá cuando no existan paquetes activos.
MSG_NO_HAY_PAQUETES_ACTIVOS = (
    "No se encuentran paquetes activos en este momento."
)

def _paquete_to_dict(paquete):
    return {
        "estado":paquete.estado,
        "repartidor":paquete.repartidor,
        "nombre":paquete.nombre,
        "comercio":paquete.comercio,
        "cliente":paquete.cliente,
        "comprobante":paquete.comprobante,
        "tamanio":paquete.tamanio,
        "cod_seguimiento":paquete.cod_seguimiento,
        "fecha_origen":paquete.fecha_origen,
        "fecha_destino":paquete.fecha_destino,
    }

def paquetesEnCurso(request):
    """
        Endpoint que devuelve todos los paquetes activos.

        Método HTTP permitido: GET.

        Respuestas:
        - 200: consulta exitosa, con paquetes o lista vacía.
        - 405: se utilizó un método HTTP no permitido.
        """

    # Verifica que la petición HTTP sea GET.
    # Este endpoint solamente consulta información;
    # no crea, modifica ni elimina paquetes.
    if request.method != "GET":
        return JsonResponse(
            {"error": "Método no permitido."},
            status=405,
        )

    # Consulta la base de datos mediante el ORM de Django.
    # La base de producción usa "DISPONIBLE" (además del valor legado
    # "ACTIVO"). Normalizamos mayúsculas/espacios y aceptamos ambos para
    # que el contrato funcione con datos existentes y registros nuevos.
    paquetes = (
        Paquete.objects.exclude(estado__iexact=Paquete.Estado.ENTREGADO)
        .select_related("comercio", "cliente", "paquete", "comprobante")
    )

    # Comprueba si la consulta devolvió algún resultado.
    # Si no hay paquetes activos, devuelve una lista vacía
    # y un mensaje informativo para el frontend.
    if not paquetes.exists():
        return JsonResponse(
            {
                "mensaje": MSG_NO_HAY_PAQUETES_ACTIVOS,
                "paquetes": [],
            },
            status=200,
        )

    # Convierte cada objeto paquete en un diccionario.
    # La comprensión de listas genera una lista de diccionarios
    # que luego podrá convertirse en JSON.
    data = [
        _paquete_to_dict(paquete)
        for paquete in paquetes
    ]

    # Devuelve los datos en formato JSON con el código HTTP 200,
    # que indica que la petición se procesó correctamente.
    return JsonResponse(
        {"paquetes": data},
        status=200,
    )
