import json

from django.db import IntegrityError
from django.views.decorators.http import require_POST, require_http_methods
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


def _repartidor_edicion_to_dict(repartidor):
    """Datos que el front necesita para precargar el formulario de edición.

    Son solo los campos de la HU #39 (no incluye el id ni el estado).
    """
    return {
        "nombre": repartidor.nombre,
        "apellido": repartidor.apellido,
        "dni": repartidor.dni,
        "telefono": repartidor.telefono,
        "mail": repartidor.mail,
        "tipo_vehiculo": repartidor.tipo_vehiculo,
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

# Mensajes requeridos por la historia de usuario #25.
MSG_ALTA_EXITOSA = "Repartidor cargado con éxito"
MSG_CAMPO_OBLIGATORIO = "Campo obligatorio"
MSG_DATO_REPETIDO = "Este dato ya existe en el sistema"

# Mensajes requeridos por la historia de usuario #39.
MSG_EDICION_EXITOSA = "Repartidor modificado con éxito"
MSG_NO_ENCONTRADO = "Repartidor no encontrado."


def _validar_datos(data, excluir_pk=None):
    """Valida los datos del alta o de la edición de un repartidor.

    excluir_pk: en una edición, es el id del repartidor que se está editando.
    Se lo excluye de la búsqueda de repetidos para que no choque consigo mismo.

    Devuelve un diccionario con los errores encontrados, usando el nombre
    del campo como clave. Si no hay errores, devuelve un diccionario vacío.
    """
    errores = {}

    # En el alta se compara con todos los repartidores; en la edición,
    # con todos menos el que se está editando.
    otros = Repartidor.objects.all()
    if excluir_pk is not None:
        otros = otros.exclude(pk=excluir_pk)

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
            if otros.filter(dni=dni).exists():
                errores["dni"] = MSG_DATO_REPETIDO

    # Escenario 3: el mail y el teléfono tampoco pueden repetirse.
    for campo in ("mail", "telefono"):
        if campo not in errores:
            valor = str(data[campo]).strip()

            if otros.filter(**{f"{campo}__iexact": valor}).exists():
                errores[campo] = MSG_DATO_REPETIDO

    # Comprueba que el tipo de vehículo coincida con una opción definida
    # en las opciones del modelo Repartidor.
    if "tipo_vehiculo" not in errores:
        if data["tipo_vehiculo"] not in Repartidor.TipoVehiculo.values:
            errores["tipo_vehiculo"] = "Tipo de vehículo inválido"

    return errores


def _normalizar_nombre(texto):
    """Deja el texto con la primera letra de cada palabra en mayúscula.

    '  jUAN   carlos ' -> 'Juan Carlos'
    """
    # split() saca espacios de más; join los une con uno solo; title() capitaliza
    return " ".join(str(texto or "").split()).title()


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
    errores = _validar_datos(data)

    # Si hay errores, los devuelve asociados a cada campo.
    if errores:
        return JsonResponse(errores, status=400)

    try:
        # Crea el repartidor usando los datos validados.
        # Se quitan espacios al principio y al final de los textos.
        repartidor = Repartidor.objects.create(
            dni=int(str(data["dni"]).strip()),
            nombre=_normalizar_nombre(data["nombre"]),
            apellido=_normalizar_nombre(data["apellido"]),
            telefono=str(data["telefono"]).strip(),
            mail=str(data["mail"]).strip().lower(),
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


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def repartidor_detalle(request, pk):
    """/api/repartidores/<pk>/ — datos y edición de un repartidor.

    GET: devuelve los datos para precargar el formulario de edición.
    PUT: guarda los cambios (HU #39).

    Devuelve:
        200: GET con los datos, o PUT con el mensaje de éxito.
        400: Si el JSON es inválido o hay errores de validación.
        404: Si el repartidor no existe.
    """
    # Busca el repartidor; si no existe, first() devuelve None.
    repartidor = Repartidor.objects.filter(pk=pk).first()
    if repartidor is None:
        return JsonResponse({"message": MSG_NO_ENCONTRADO}, status=404)

    if request.method == "GET":
        return JsonResponse({"repartidor": _repartidor_edicion_to_dict(repartidor)})

    # --- PUT ---
    data = _parse_body(request)
    if data is None:
        return JsonResponse(
            {"message": "El cuerpo debe ser JSON válido."},
            status=400,
        )

    # Misma validación que el alta, pero sin contar al propio repartidor
    # como "repetido".
    errores = _validar_datos(data, excluir_pk=repartidor.pk)
    if errores:
        return JsonResponse(errores, status=400)

    # Se actualizan solo los datos editables.
    # El token y el estado NO se tocan: el token se mantiene al editar.
    repartidor.dni = int(str(data["dni"]).strip())
    repartidor.nombre = _normalizar_nombre(data["nombre"])
    repartidor.apellido = _normalizar_nombre(data["apellido"])
    repartidor.telefono = str(data["telefono"]).strip()
    repartidor.mail = str(data["mail"]).strip().lower()
    repartidor.tipo_vehiculo = data["tipo_vehiculo"]

    try:
        repartidor.save()
    except IntegrityError:
        # Dos ediciones simultáneas podrían chocar en la base de datos.
        return JsonResponse({"dni": MSG_DATO_REPETIDO}, status=400)

    # El front solo necesita el mensaje.
    return JsonResponse({"message": MSG_EDICION_EXITOSA})