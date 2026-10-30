"""
Endpoint del panel "Paquetes en curso" (HU #40).

    GET /api/dashboard/paquetes-en-curso/

Responde ``{"paquetes": [...]}`` con los paquetes que todavía están en curso
(todos salvo ``entregado``). ``cancelado`` es un estado intermediario, así que
también se lista. Cada ítem sigue el contrato que consume
``frontend/src/pages/PaquetesEnCurso.tsx``::

    {
        "id": 1,
        "destinatario": "Ana Pérez",
        "direccion": "Calle 12 #34",
        "repartidor": "Juan Gómez",     # "Sin asignar" si no tiene repartidor
        "estado": "en_camino"
    }

Los valores son primitivos: las FKs del modelo (``cliente``, ``repartidor``,
``comercio``, ``comprobante``) son objetos Django y no se pueden devolver
directamente en un ``JsonResponse``. ``select_related`` trae solo las dos FKs
que se serializan, en el mismo query (un JOIN por FK, sin N+1). La relación
``paquete`` NO existe en ``Paquete``: es el nombre inverso de
``Comprobante.paquete``, por eso no puede ir en ``select_related``.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Importa el modelo Paquete definido en la aplicación core.
from core.models import Paquete


# Mensaje que se devuelve cuando no existen paquetes en curso.
MSG_NO_HAY_PAQUETES_ACTIVOS = (
    "No se encuentran paquetes activos en este momento."
)
# Texto para los paquetes que todavía no tienen repartidor asignado.
MSG_SIN_REPARTIDOR = "Sin asignar"


def _nombre_completo(persona):
    """Nombre + apellido de un Cliente/Repartidor, sin espacios sobrantes."""
    return f"{persona.nombre} {persona.apellido}".strip()


def _paquete_to_dict(paquete):
    """Serializa un ``Paquete`` a las cinco claves que espera el frontend."""
    return {
        "id": paquete.id,
        "destinatario": _nombre_completo(paquete.cliente),
        "direccion": paquete.cliente.direccion,
        "repartidor": (
            _nombre_completo(paquete.repartidor)
            if paquete.repartidor
            else MSG_SIN_REPARTIDOR
        ),
        "estado": paquete.estado,
        "tamanio": paquete.tamanio,
    }


@csrf_exempt  # solo lectura: así un POST llega al 405 y no lo frena el CSRF (403)
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
    # El único estado final es "entregado"; "cancelado" es intermediario y
    # debe seguir apareciendo en el panel. iexact tolera valores históricos en
    # mayúsculas porque la columna es un varchar libre.
    # select_related solo admite FKs directas de Paquete: repartidor, comercio,
    # cliente y comprobante. Acá alcanza con repartidor y cliente, que son las
    # que usa el serializador.
    paquetes = (
        Paquete.objects.exclude(estado__iexact=Paquete.Estado.ENTREGADO)
        .select_related("repartidor", "cliente")
    )

    # Se evalúa el queryset una sola vez (evita el exists() + iteración, que
    # ejecutaba dos consultas) y se convierte cada paquete en un diccionario.
    data = [_paquete_to_dict(paquete) for paquete in paquetes]

    # Si no hay paquetes en curso, devuelve una lista vacía
    # y un mensaje informativo para el frontend.
    if not data:
        return JsonResponse(
            {
                "mensaje": MSG_NO_HAY_PAQUETES_ACTIVOS,
                "paquetes": [],
            },
            status=200,
        )

    # Devuelve los datos en formato JSON con el código HTTP 200,
    # que indica que la petición se procesó correctamente.
    return JsonResponse(
        {"paquetes": data},
        status=200,
    )
