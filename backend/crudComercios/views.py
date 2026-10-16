"""
API REST para el CRUD de Comercios.

Expone endpoints JSON que consume el frontend React (y cualquier otro
cliente). No usamos Django REST Framework para mantener las dependencias
al mínimo: las vistas leen/escriben JSON a mano con ``JsonResponse``.

Rutas (ver crudComercios/urls.py):
    GET    /api/comercios/        -> lista (con ?q= para filtrar por nombre)
    POST   /api/comercios/        -> crea
    GET    /api/comercios/<id>/   -> detalle
    PUT    /api/comercios/<id>/   -> reemplaza
    PATCH  /api/comercios/<id>/   -> actualiza parcialmente
    DELETE /api/comercios/<id>/   -> borra
"""

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.models import Cliente, Comercio


def _parse_body(request):
    """Devuelve el dict del body JSON o None si no es JSON válido."""
    if not request.body:
        return {}
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _comercio_to_dict(comercio):
    return {
        "id": comercio.id,
        "nombre": comercio.nombre,
        "telefono": comercio.telefono,
        "direccion": comercio.direccion,
        "datos_cliente": comercio.datos_cliente_id,
    }


def _validar_y_aplicar(comercio, data, parcial=False):
    """
    Aplica los campos presentes en ``data`` a ``comercio``.

    Devuelve (ok, error_response). Si ok es False, error_response es un
    JsonResponse con el detalle del error.
    """
    # nombre
    if "nombre" in data:
        nombre = data.get("nombre")
        if not isinstance(nombre, str) or not nombre.strip():
            return False, JsonResponse(
                {"nombre": "El nombre es obligatorio."}, status=400
            )
        comercio.nombre = nombre.strip()
    elif not parcial:
        return False, JsonResponse(
            {"nombre": "El nombre es obligatorio."}, status=400
        )

    # telefono
    if "telefono" in data:
        telefono = data.get("telefono")
        if not isinstance(telefono, str) or not telefono.strip():
            return False, JsonResponse(
                {"telefono": "El teléfono es obligatorio."}, status=400
            )
        comercio.telefono = telefono.strip()
    elif not parcial:
        return False, JsonResponse(
            {"telefono": "El teléfono es obligatorio."}, status=400
        )

    # direccion
    if "direccion" in data:
        direccion = data.get("direccion")
        if not isinstance(direccion, str) or not direccion.strip():
            return False, JsonResponse(
                {"direccion": "La dirección es obligatoria."}, status=400
            )
        comercio.direccion = direccion.strip()
    elif not parcial:
        return False, JsonResponse(
            {"direccion": "La dirección es obligatoria."}, status=400
        )

    # datos_cliente (FK opcional)
    if "datos_cliente" in data:
        valor = data.get("datos_cliente")
        if valor is None or valor == "":
            comercio.datos_cliente = None
        else:
            try:
                cliente = Cliente.objects.get(pk=valor)
            except (Cliente.DoesNotExist, ValueError, TypeError):
                return False, JsonResponse(
                    {"datos_cliente": "Cliente no encontrado."}, status=400
                )
            comercio.datos_cliente = cliente

    return True, None


@csrf_exempt
def comercios_list(request):
    """Lista todos los comercios o crea uno nuevo."""
    if request.method == "GET":
        qs = Comercio.objects.all()
        q = request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(nombre__icontains=q)
        return JsonResponse(
            {"results": [_comercio_to_dict(c) for c in qs], "count": qs.count()},
            status=200,
        )

    if request.method == "POST":
        data = _parse_body(request)
        if data is None:
            return JsonResponse(
                {"detail": "El cuerpo debe ser JSON válido."}, status=400
            )
        comercio = Comercio()
        ok, err = _validar_y_aplicar(comercio, data, parcial=False)
        if not ok:
            return err
        comercio.save()
        return JsonResponse(_comercio_to_dict(comercio), status=201)

    return JsonResponse({"detail": "Método no permitido."}, status=405)


@csrf_exempt
def comercio_detail(request, pk):
    """Detalle, actualización y borrado de un comercio."""
    try:
        comercio = Comercio.objects.get(pk=pk)
    except Comercio.DoesNotExist:
        return JsonResponse({"detail": "Comercio no encontrado."}, status=404)

    if request.method == "GET":
        return JsonResponse(_comercio_to_dict(comercio), status=200)

    if request.method in ("PUT", "PATCH"):
        data = _parse_body(request)
        if data is None:
            return JsonResponse(
                {"detail": "El cuerpo debe ser JSON válido."}, status=400
            )
        parcial = request.method == "PATCH"
        ok, err = _validar_y_aplicar(comercio, data, parcial=parcial)
        if not ok:
            return err
        comercio.save()
        return JsonResponse(_comercio_to_dict(comercio), status=200)

    if request.method == "DELETE":
        comercio.delete()
        return JsonResponse({}, status=204)

    return JsonResponse({"detail": "Método no permitido."}, status=405)
