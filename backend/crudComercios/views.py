"""
API REST para el CRUD de Comercios.

Expone endpoints JSON que consume el frontend React (``frontend/src/pages/Comercios.tsx``)
y cualquier otro cliente. No usa Django REST Framework para mantener las dependencias
al mínimo: las vistas leen/escriben JSON a mano con ``JsonResponse``.

Rutas (ver ``crudComercios/urls.py`` — prefijo global ``/api/`` en ``config/urls.py``):

    GET    /api/comercios/        → lista (con ``?q=`` para filtrar por ``nombre``)
    POST   /api/comercios/        → crea
    GET    /api/comercios/<id>/   → detalle
    PUT    /api/comercios/<id>/   → reemplaza (todos los campos obligatorios)
    PATCH  /api/comercios/<id>/   → actualiza parcialmente (solo lo enviado)
    DELETE /api/comercios/<id>/   → borra

Contrato JSON (ejemplo) — producido por ``_comercio_to_dict``::

    {
        "id": 1,
        "nombre": "Kiosco Central",
        "telefono": "221-555-0100",
        "direccion": "Calle 7 #123"
    }

Listado → ``{"results": [...], "count": N}``.
Errores → ``400`` con la clave del campo (``{"nombre": "…"}``) o ``{"detail": "…"}``.

Dependencias
------------
- Modelo: ``core.models.Comercio`` (única fuente de verdad del esquema).
- Cada helper está documentado abajo; las vistas delegan validación a ``_validar_y_aplicar``.

Cambio de esquema: ``Comercio.datos_cliente`` (``id_datos_cliente`` del diagrama)
**salió** de la base, así que la API ya no lo expone ni lo valida. Si un cliente
aún lo envía, se ignora (los campos desconocidos nunca fueron error).
"""

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.models import Comercio


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

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


def _comercio_to_dict(comercio):
    """Serializa un ``Comercio`` al contrato JSON de la API.

    El comercio es una tabla simple (nombre, teléfono, dirección): desde el
    cambio de esquema ya no referencia un cliente, así que no hay FK que
    serializar. El vínculo comercio ↔ cliente se ve en ``Paquete``.

    Args:
        comercio: instancia ``core.models.Comercio`` (guardada o no).

    Returns:
        dict con ``id``, ``nombre``, ``telefono`` y ``direccion``.
    """
    return {
        "id": comercio.id,
        "nombre": comercio.nombre,
        "telefono": comercio.telefono,
        "direccion": comercio.direccion,
    }


def _validar_y_aplicar(comercio, data, parcial=False):
    """Valida ``data`` y aplica los campos a ``comercio`` en memoria.

    La función **no guarda** en la BD; solo muta el objeto. El llamante debe
    hacer ``comercio.save()`` si ``ok`` es ``True``.

    Reglas de validación:

    - ``nombre``, ``telefono``, ``direccion``: ``str`` no vacío tras ``strip()``.
      Obligatorios si ``parcial is False`` (``POST``/``PUT``). En ``PATCH`` solo
      se validan si vienen en ``data``.
    - Cualquier otra clave (incluido el ya inexistente ``datos_cliente``) se ignora.

    Args:
        comercio: instancia ``Comercio`` a mutar (puede ser ``Comercio()`` nuevo).
        data: dict decodificado del body JSON.
        parcial: si ``True``, los tres campos de texto son opcionales (``PATCH``).

    Returns:
        tuple[bool, JsonResponse|None]: ``(True, None)`` si validó;
        ``(False, JsonResponse(status=400))`` con el detalle del primer error.
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

    return True, None


# ---------------------------------------------------------------------------
# Vistas
# ---------------------------------------------------------------------------

@csrf_exempt
def comercios_list(request):
    """Lista o crea comercios.

    ``GET /api/comercios/?q=<texto>``
        Lista todos los comercios. Si se pasa ``q``, filtra con
        ``nombre__icontains`` (búsqueda parcial, case-insensitive).

        Respuesta ``200``::

            {"results": [{...}, {...}], "count": N}

    ``POST /api/comercios/``
        Crea un comercio. Body JSON con ``nombre``, ``telefono``, ``direccion``
        (obligatorios). Cualquier otra clave se ignora.

        Respuestas::

            201 → comercio creado (JSON del comercio)
            400 → falta campo / JSON inválido / cliente inexistente

    Cualquier otro método → ``405 {"detail": "Método no permitido."}``.
    """
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
    """Detalle, actualización y borrado de un comercio.

    ``GET /api/comercios/<pk>/``
        Devuelve el comercio. ``404`` si no existe.

    ``PUT /api/comercios/<pk>/``
        Reemplazo total: exige ``nombre``, ``telefono``, ``direccion``.
        ``200`` con el comercio actualizado o ``400``.

    ``PATCH /api/comercios/<pk>/``
        Actualización parcial: solo valida los campos enviados.
        Ideal para ``{"telefono": "nuevo"}``.

    ``DELETE /api/comercios/<pk>/``
        Borra. ``204`` con body ``{}``. ``404`` si no existe.

    Cualquier otro método → ``405``.
    """
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
