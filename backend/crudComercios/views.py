"""
API REST para el CRUD de Comercios.

Expone endpoints JSON que consume el frontend React (``frontend/src/pages/Comercios.tsx``)
y cualquier otro cliente. No usa Django REST Framework para mantener las dependencias
al mínimo: las vistas leen/escriben JSON a mano con ``JsonResponse``
(``HttpResponse`` vacío para el borrado).

Rutas (ver ``crudComercios/urls.py`` — prefijo global ``/api/`` en ``config/urls.py``):

    GET    /api/comercios/        → lista (con ``?q=`` para filtrar por ``nombre``)
    POST   /api/comercios/        → crea
    GET    /api/comercios/<id>/   → detalle
    PUT    /api/comercios/<id>/   → reemplaza (todos los campos obligatorios)
    PATCH  /api/comercios/<id>/   → actualiza parcialmente (solo lo enviado)
    DELETE /api/comercios/<id>/   → borra (204 sin body)

Contrato JSON (ejemplo) — producido por ``_comercio_to_dict``::

    {
        "id": 1,
        "nombre": "Kiosco Central",
        "telefono": "221-555-0100",
        "direccion": "Calle 7 #123"
    }

La respuesta tiene exactamente las cuatro columnas de la tabla ``comercio``: ``comercio``
no referencia a ningún cliente, así que no hay FK que serializar.

Listado → ``{"results": [...], "count": N}``.
Errores → ``400`` con la clave del campo (``{"nombre": "…"}``) o ``{"detail": "…"}``.
Los campos que el modelo no tiene se ignoran en silencio (nunca fueron error).

Dependencias
------------
- Modelo: ``core.models.Comercio`` (única fuente de verdad del esquema).
- Cada helper está documentado abajo; las vistas delegan validación a ``_validar_y_aplicar``.
"""

import json

from django.http import HttpResponse, JsonResponse
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

    Son las cuatro columnas de la tabla, sin anidados: el comercio no
    referencia clientes (el vínculo se consulta por ``Paquete``), así que no
    hay FK que resolver ni consultas extra que hacer por comercio.

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
    - Cualquier otra clave de ``data`` se ignora: no se guarda ni se rechaza.
    - ``nombre`` y ``direccion`` no pueden repetirse con otro comercio
      (comparación sin importar mayúsculas).

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

    # No puede haber dos comercios con el mismo nombre o dirección (sin importar
    # mayúsculas). Se excluye el propio comercio para que editarlo no choque consigo.
    # Solo se revisan los campos enviados: así los repetidos que ya existen en dev
    # se pueden seguir editando (por ejemplo, el teléfono).
    otros = Comercio.objects.exclude(pk=comercio.pk)
    if "nombre" in data and otros.filter(nombre__iexact=comercio.nombre).exists():
        return False, JsonResponse(
            {"nombre": "Ya existe un comercio con ese nombre."}, status=400
        )
    if "direccion" in data and otros.filter(direccion__iexact=comercio.direccion).exists():
        return False, JsonResponse(
            {"direccion": "Ya existe un comercio con esa dirección."}, status=400
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
        Borra. ``204`` **sin body** (así lo exige HTTP y así lo parsea el proxy de
        Vite). ``404`` si no existe.

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
        # 204 con body vacío a propósito: un "No Content" con Content-Length>0
        # (ej. JsonResponse({})) rompe el parser HTTP del proxy de Vite y el
        # DELETE llega al navegador como 502 aunque haya borrado.
        return HttpResponse(status=204)

    return JsonResponse({"detail": "Método no permitido."}, status=405)
