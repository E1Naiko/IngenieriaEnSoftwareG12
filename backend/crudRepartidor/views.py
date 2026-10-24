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

"""Alta de repartidor (HU #25): el coordinador carga un repartidor."""

CAMPOS_OBLIGATORIOS = ["dni", "nombre", "apellido", "telefono", "mail", "tipo_vehiculo"]

# Mensajes exactos que pide la HU
MSG_ALTA_EXITOSA = "Repartidor cargado con éxito"
MSG_CAMPO_OBLIGATORIO = "Campo obligatorio"
MSG_DATO_REPETIDO = "Este dato ya existe en el sistema"

# Campos que el coordinador tiene que completar (el token lo genera el sistema)
CAMPOS_OBLIGATORIOS = ["dni", "nombre", "apellido", "telefono", "mail", "tipo_vehiculo"]

# Mensajes exactos que pide la HU
MSG_ALTA_EXITOSA = "Repartidor cargado con éxito"
MSG_CAMPO_OBLIGATORIO = "Campo obligatorio"
MSG_DATO_REPETIDO = "Este dato ya existe en el sistema"


def _validar_alta(data):
    """Revisa los datos del alta. Devuelve un dict {campo: mensaje} con los errores.

    Si el dict vuelve vacío, los datos están bien.
    """
    errores = {}

    # Escenario 2: ningún campo puede estar vacío
    for campo in CAMPOS_OBLIGATORIOS:
        if not str(data.get(campo) or "").strip():
            errores[campo] = MSG_CAMPO_OBLIGATORIO

    # Escenario 3: el DNI no puede repetirse
    if "dni" not in errores:
        try:
            dni = int(str(data["dni"]).strip())
        except ValueError:
            errores["dni"] = "El DNI debe ser un número"
        else:
            if Repartidor.objects.filter(dni=dni).exists():
                errores["dni"] = MSG_DATO_REPETIDO

    # Escenario 3: el mail y el teléfono tampoco
    for campo in ("mail", "telefono"):
        if campo not in errores:
            valor = str(data[campo]).strip()
            if Repartidor.objects.filter(**{campo: valor}).exists():
                errores[campo] = MSG_DATO_REPETIDO

    # El tipo de vehículo tiene que ser uno de los permitidos
    if "tipo_vehiculo" not in errores:
        if data["tipo_vehiculo"] not in Repartidor.TipoVehiculo.values:
            errores["tipo_vehiculo"] = "Tipo de vehículo inválido"

    return errores

@csrf_exempt  # igual que el resto de la API
@require_POST  # cualquier otro método responde 405
def repartidores_alta(request):
    """POST /api/repartidores/ — da de alta un repartidor.

    201 → alta exitosa (el sistema genera el token y lo devuelve).
    400 → JSON inválido, o campos en blanco / repetidos ({campo: mensaje}).
    """
    data = _parse_body(request)
    if data is None:
        return JsonResponse({"message": "El cuerpo debe ser JSON válido."}, status=400)

    # Escenarios 2 y 3: campos en blanco o datos repetidos
    errores = _validar_alta(data)
    if errores:
        return JsonResponse(errores, status=400)

    try:
        repartidor = Repartidor.objects.create(
            dni=int(str(data["dni"]).strip()),
            nombre=str(data["nombre"]).strip(),
            apellido=str(data["apellido"]).strip(),
            telefono=str(data["telefono"]).strip(),
            mail=str(data["mail"]).strip(),
            tipo_vehiculo=data["tipo_vehiculo"],
        )
    except IntegrityError:
        # Dos altas con el mismo DNI al mismo tiempo: la base lo frena igual
        return JsonResponse({"dni": MSG_DATO_REPETIDO}, status=400)

    # Escenario 1: el repartidor se guardó y el sistema le generó su token
    return JsonResponse(
        {
            "message": MSG_ALTA_EXITOSA,
            "repartidor": _repartidor_to_dict(repartidor),
        },
        status=201,
    )
