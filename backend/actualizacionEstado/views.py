"""Vistas para actualizar el estado de los paquetes/pedidos (HU #34)."""

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from core.models import Paquete


def to_dict(paquete):
    """
    Convierte un objeto Paquete en un diccionario para enviar al frontend.
    """
    return {
        "id": paquete.id,
        "cod_seguimiento": paquete.cod_seguimiento,
        "estado": paquete.estado,
        "tamanio": paquete.tamanio,
        "fecha_origen": str(paquete.fecha_origen) if paquete.fecha_origen else None,
        "fecha_destino": str(paquete.fecha_destino) if paquete.fecha_destino else None,
        "id_repartidor_asignado": paquete.repartidor.id if paquete.repartidor else None,
        "id_comercio": paquete.comercio.id,
        "id_cliente": paquete.cliente.id,
    }


@csrf_exempt
@require_http_methods(["GET", "POST"])
def cambiar_estado_pedido(request):
    """
    GET /api/cambiar-estado-pedido/
        Lista todos los paquetes existentes.
        Opcional: ?cod_seguimiento=SRFR-XXXX para filtrar por uno específico.

    POST /api/cambiar-estado-pedido/
        Actualiza el estado de un paquete específico.
        Body JSON esperado: {"id": <id_paquete>, "estado": "pendiente" | "en_camino" | "entregado" | "cancelado"}
    """

    # --- GET: Listar paquetes ---
    if request.method == "GET":
        cod_seguimiento = request.GET.get("cod_seguimiento")

        if cod_seguimiento:
            paquetes = Paquete.objects.filter(cod_seguimiento=cod_seguimiento)
        else:
            paquetes = Paquete.objects.all()

        # Usamos .exists() para verificar si hay paquetes
        if not paquetes.exists():
            return JsonResponse(
                {"message": "No hay paquetes registrados.", "paquetes": []},
                status=200
            )

        lista_paquetes = [to_dict(p) for p in paquetes]
        return JsonResponse(
            {"message": "Paquetes obtenidos correctamente.", "paquetes": lista_paquetes},
            status=200
        )

    # --- POST: Actualizar estado de un paquete ---
    if request.method == "POST":
        # Parsear JSON
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"message": "El cuerpo debe ser JSON válido."}, status=400)

        if not isinstance(data, dict):
            return JsonResponse({"message": "El cuerpo debe ser un objeto JSON."}, status=400)

        # Obtener id y nuevo estado
        paquete_id = data.get("id")
        nuevo_estado = data.get("estado")

        if paquete_id is None:
            return JsonResponse({"message": "Falta el campo 'id' del paquete."}, status=400)

        if nuevo_estado is None:
            return JsonResponse({"message": "Falta el campo 'estado'."}, status=400)

        # Validar que el estado sea válido
        estados_validos = [e.value for e in Paquete.Estado]
        if nuevo_estado not in estados_validos:
            return JsonResponse(
                {"message": f"Estado inválido. Debe ser uno de: {', '.join(estados_validos)}"},
                status=400
            )

        # Buscar el paquete por ID
        paquetes = Paquete.objects.filter(id=paquete_id)

        # Usar .exists() para verificar si existe
        if not paquetes.exists():
            return JsonResponse(
                {"message": f"No se encontró un paquete con id={paquete_id}."},
                status=404
            )

        # Obtener el paquete y actualizar
        paquete = paquetes.first()

        # Validación extra: no se puede modificar un paquete ya entregado o cancelado
        if paquete.estado in [Paquete.Estado.ENTREGADO, Paquete.Estado.CANCELADO]:
            return JsonResponse(
                {"message": f"No se puede modificar el estado de un paquete '{paquete.estado}'."},
                status=400
            )

        paquete.estado = nuevo_estado
        paquete.save()

        return JsonResponse(
            {
                "message": "Estado del paquete actualizado correctamente.",
                "paquete": to_dict(paquete),
            },
            status=200
        )