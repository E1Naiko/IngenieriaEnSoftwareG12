import json

from django.db import IntegrityError
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.models import Repartidor


def _parse_body(request):
    """Intenta leer el body de la petición como un objeto JSON.

    Devuelve:
        dict: Los datos recibidos, si el JSON es válido y es un objeto.
        {}: Si el body está vacío, para que la validación informe los
            campos obligatorios que faltan.
        None: Si el JSON es inválido o no representa un objeto
            (por ejemplo, si es una lista o un número).
    """
    # Si no hay body, se devuelve un diccionario vacío.
    if not request.body:
        return {}

    try:
        # El body llega como bytes; se decodifica a texto y luego a JSON.
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        # El contenido no tiene formato JSON válido o no está codificado en UTF-8.
        return None

    # La API espera un objeto JSON, no una lista, cadena, número, etc.
    if not isinstance(data, dict):
        return None

    return data


def _repartidor_to_dict(repartidor):
    """Convierte un repartidor en un diccionario listo para devolver como JSON."""
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


# Campos que el coordinador debe completar al dar de alta un repartidor.
# El token no se solicita en la petición.
CAMPOS_OBLIGATORIOS = [
    "dni",
    "nombre",
    "apellido",
    "telefono",
    "mail",
    "tipo_vehiculo",
]

# Mensajes requeridos por la historia de usuario.
MSG_ALTA_EXITOSA = "Repartidor cargado con éxito"
MSG_CAMPO_OBLIGATORIO = "Campo obligatorio"
MSG_DATO_REPETIDO = "Este dato ya existe en el sistema"


def _validar_alta(data):
    """Valida los datos del alta.

    Devuelve un diccionario con los errores encontrados, usando el nombre
    del campo como clave. Si no hay errores, devuelve un diccionario vacío.
    """
    errores = {}

    # Escenario 2: comprueba que todos los campos requeridos tengan contenido.
    # También considera vacío un texto compuesto solo por espacios.
    for campo in CAMPOS_OBLIGATORIOS:
        if not str(data.get(campo) or "").strip():
            errores[campo] = MSG_CAMPO_OBLIGATORIO

    # Escenario 3: el DNI debe ser numérico y no debe estar registrado.
    # No se valida de nuevo si ya se marcó como obligatorio.
    if "dni" not in errores:
        try:
            dni = int(str(data["dni"]).strip())
        except ValueError:
            errores["dni"] = "El DNI debe ser un número"
        else:
            if Repartidor.objects.filter(dni=dni).exists():
                errores["dni"] = MSG_DATO_REPETIDO

    # Escenario 3: el mail y el teléfono tampoco pueden repetirse.
    for campo in ("mail", "telefono"):
        if campo not in errores:
            valor = str(data[campo]).strip()

            if Repartidor.objects.filter(**{campo: valor}).exists():
                errores[campo] = MSG_DATO_REPETIDO

    # Comprueba que el tipo de vehículo coincida con una opción definida
    # en las opciones del modelo Repartidor.
    if "tipo_vehiculo" not in errores:
        if data["tipo_vehiculo"] not in Repartidor.TipoVehiculo.values:
            errores["tipo_vehiculo"] = "Tipo de vehículo inválido"

    return errores


@csrf_exempt  # Desactiva la validación CSRF para este endpoint.
@require_POST  # Acepta únicamente POST; los demás métodos reciben 405.
def repartidores_alta(request):
    """POST /api/repartidores/ — da de alta un repartidor.

    Devuelve:
        201: Si el repartidor se creó correctamente.
        400: Si el JSON es inválido o hay errores de validación.
    """
    # Lee y decodifica los datos enviados en el body.
    data = _parse_body(request)

    # Si el JSON no es válido o no es un objeto, devuelve un error general.
    if data is None:
        return JsonResponse(
            {"message": "El cuerpo debe ser JSON válido."},
            status=400,
        )

    # Valida campos obligatorios, duplicados y tipo de vehículo.
    errores = _validar_alta(data)

    # Si hay errores, los devuelve asociados a cada campo.
    if errores:
        return JsonResponse(errores, status=400)

    try:
        # Crea el repartidor usando los datos validados.
        # Se quitan espacios al principio y al final de los textos.
        repartidor = Repartidor.objects.create(
            dni=int(str(data["dni"]).strip()),
            nombre=str(data["nombre"]).strip(),
            apellido=str(data["apellido"]).strip(),
            telefono=str(data["telefono"]).strip(),
            mail=str(data["mail"]).strip(),
            tipo_vehiculo=data["tipo_vehiculo"],
        )
    except IntegrityError:
        # La base de datos también puede detectar datos duplicados,
        # por ejemplo, si dos altas ocurren al mismo tiempo.
        return JsonResponse({"dni": MSG_DATO_REPETIDO}, status=400)

    # Si se guardó correctamente, devuelve el mensaje y los datos del repartidor.
    return JsonResponse(
        {
            "message": MSG_ALTA_EXITOSA,
            "repartidor": _repartidor_to_dict(repartidor),
        },
        status=201,
    )