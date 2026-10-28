"""
Ingresar pedido (HU #37).

El coordinador carga a mano los pedidos que le llegan por WhatsApp. Cada
pedido se guarda como un ``core.models.Paquete``.

Rutas (prefijo global ``/api/`` en ``config/urls.py``):

    GET  /api/pedidos/   → lista de pedidos
    POST /api/pedidos/   → carga un pedido
    GET  /api/clientes/  → lista de clientes (para el selector del front)
    POST /api/clientes/  → alta de cliente (desde el popup del front)

Body del POST de pedidos::

    {
        "comercio": 1,                  // id de Comercio
        "cliente": 4,                   // id de Cliente
        "tamanio": "chico",             // chico | mediano | grande
        "fecha_destino": "2026-10-30",  // fecha de entrega, no puede ser pasada
        "fecha_origen": "2026-10-27",   // opcional, por defecto hoy
        "forzar": true                  // opcional: cargarlo aunque haya uno similar
    }

Respuestas según los escenarios de la HU:

    201 → pedido cargado (escenario 1)
    400 → {"<campo>": "Campo obligatorio *"} por cada campo vacío (escenario 2)
    400 → {"<campo>": "Fecha invalida"} (escenario 3)
    409 → {"detail": "Hay un pedido similar…", "similar": {...}} (escenario 4)
"""

from datetime import date

from django.db.models.functions import Trim, Upper
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from core.models import Cliente, Comercio, Paquete
from crudComercios.views import _parse_body

# Mensajes que pide la HU
MSG_OBLIGATORIO = "Campo obligatorio *"
MSG_FECHA_INVALIDA = "Fecha invalida"
MSG_SIMILAR = "Hay un pedido similar ¿Desea cargarlo igualmente?"

CAMPOS_PEDIDO = ("comercio", "cliente", "tamanio", "fecha_destino")
CAMPOS_CLIENTE = ("nombre", "apellido", "telefono", "direccion", "dni")

# Solo un pedido cancelado no cuenta como similar: el 409 es una advertencia,
# así que también se avisa si el similar ya fue entregado.
# shortcut: la base de dev guarda estados en mayúscula (mismo parche que #33);
# sacar el Upper/Trim cuando se normalicen los datos.
ESTADO_EXCLUIDO = Paquete.Estado.CANCELADO.upper()


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _faltantes(data, campos):
    """Devuelve ``{campo: MSG_OBLIGATORIO}`` por cada campo ausente o vacío."""
    return {
        c: MSG_OBLIGATORIO
        for c in campos
        if data.get(c) is None or str(data.get(c)).strip() == ""
    }


def _buscar(modelo, pk):
    """Instancia de ``modelo`` con ese pk, o ``None`` si no existe o el pk no es válido."""
    try:
        return modelo.objects.get(pk=pk)
    except (modelo.DoesNotExist, ValueError, TypeError):
        return None


def _parse_fecha(valor):
    """Convierte ``AAAA-MM-DD`` en ``date``; ``None`` si el formato no es válido."""
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        return None


def _pedido_to_dict(p):
    """Serializa un ``Paquete`` al contrato JSON de la API."""
    return {
        "id": p.id,
        "cod_seguimiento": p.cod_seguimiento,
        "estado": p.estado,
        "tamanio": p.tamanio,
        "comercio": p.comercio_id,
        "cliente": p.cliente_id,
        "fecha_origen": p.fecha_origen.isoformat(),
        "fecha_destino": p.fecha_destino.isoformat(),
    }


def _cliente_to_dict(c):
    """Serializa un ``Cliente`` al contrato JSON de la API."""
    return {
        "id": c.id,
        "nombre": c.nombre,
        "apellido": c.apellido,
        "telefono": c.telefono,
        "direccion": c.direccion,
        "dni": c.dni,
    }


# ---------------------------------------------------------------------------
# Vistas
# ---------------------------------------------------------------------------

@csrf_exempt
def pedidos_list(request):
    """Lista (``GET``) o carga (``POST``) pedidos. Ver docstring del módulo."""
    if request.method == "GET":
        qs = Paquete.objects.all()
        return JsonResponse(
            {"results": [_pedido_to_dict(p) for p in qs], "count": qs.count()}
        )

    if request.method != "POST":
        return JsonResponse({"detail": "Método no permitido."}, status=405)

    data = _parse_body(request)
    if data is None:
        return JsonResponse({"detail": "El cuerpo debe ser JSON válido."}, status=400)

    # Escenario 2: se informan todos los campos vacíos juntos
    errores = _faltantes(data, CAMPOS_PEDIDO)
    if errores:
        return JsonResponse(errores, status=400)

    comercio = _buscar(Comercio, data["comercio"])
    if comercio is None:
        return JsonResponse({"comercio": "Comercio no encontrado."}, status=400)
    cliente = _buscar(Cliente, data["cliente"])
    if cliente is None:
        return JsonResponse({"cliente": "Cliente no encontrado."}, status=400)
    if data["tamanio"] not in Paquete.Tamanio.values:
        return JsonResponse({"tamanio": "Tamaño inválido."}, status=400)

    # Escenario 3: la entrega no puede ser antes de hoy, ni antes del retiro
    hoy = timezone.localdate()
    fecha_destino = _parse_fecha(data["fecha_destino"])
    if fecha_destino is None or fecha_destino < hoy:
        return JsonResponse({"fecha_destino": MSG_FECHA_INVALIDA}, status=400)
    if data.get("fecha_origen") in (None, ""):
        fecha_origen = hoy
    else:
        fecha_origen = _parse_fecha(data["fecha_origen"])
        if fecha_origen is None or fecha_origen > fecha_destino:
            return JsonResponse({"fecha_origen": MSG_FECHA_INVALIDA}, status=400)

    # Escenario 4: el coordinador decide si lo carga igual reenviando con forzar=true
    similar = (
        Paquete.objects.annotate(estado_normalizado=Upper(Trim("estado")))
        .filter(comercio=comercio, cliente=cliente, fecha_destino=fecha_destino)
        .exclude(estado_normalizado=ESTADO_EXCLUIDO)
        .first()
    )
    if similar and data.get("forzar") is not True:
        return JsonResponse(
            {"detail": MSG_SIMILAR, "similar": _pedido_to_dict(similar)}, status=409
        )

    pedido = Paquete.objects.create(
        comercio=comercio,
        cliente=cliente,
        tamanio=data["tamanio"],
        fecha_origen=fecha_origen,
        fecha_destino=fecha_destino,
    )
    return JsonResponse(_pedido_to_dict(pedido), status=201)


@csrf_exempt
def clientes_list(request):
    """Lista (``GET``) o crea (``POST``) clientes. Ver ``CAMPOS_CLIENTE``."""
    if request.method == "GET":
        qs = Cliente.objects.all()
        return JsonResponse(
            {"results": [_cliente_to_dict(c) for c in qs], "count": qs.count()}
        )

    if request.method != "POST":
        return JsonResponse({"detail": "Método no permitido."}, status=405)

    data = _parse_body(request)
    if data is None:
        return JsonResponse({"detail": "El cuerpo debe ser JSON válido."}, status=400)

    errores = _faltantes(data, CAMPOS_CLIENTE)
    if errores:
        return JsonResponse(errores, status=400)

    # El front manda el DNI como número; también se acepta como texto de dígitos
    dni = str(data["dni"]).strip()
    if isinstance(data["dni"], bool) or not dni.isdigit():
        return JsonResponse({"dni": "El DNI debe ser numérico."}, status=400)
    if Cliente.objects.filter(dni=int(dni)).exists():
        return JsonResponse({"dni": "Ya existe un cliente con ese DNI."}, status=400)

    cliente = Cliente.objects.create(
        nombre=str(data["nombre"]).strip(),
        apellido=str(data["apellido"]).strip(),
        telefono=str(data["telefono"]).strip(),
        direccion=str(data["direccion"]).strip(),
        dni=int(dni),
    )
    return JsonResponse(_cliente_to_dict(cliente), status=201)
