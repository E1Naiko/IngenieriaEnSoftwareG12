"""Login del repartidor (HU #9)"""

import json

from django.http import JsonResponse 
from django.views.decorators.csrf import csrf_exempt 
from django.views.decorators.http import require_POST
from core.models import Repartidor 

#Mensaje que pide la HU para el escenario 2
MSG_TOKEN_INVALIDO = "Token inválido"
MSG_REPARTIDOR_BAJA = (
    "El repartidor no se encuentra habilitado. Comuníquese con el coordinador")

@csrf_exempt  # antes de iniciar sesión el front no tiene token CSRF
@require_POST  # cualquier otro método responde 405
def login_repartidor(request):
     # Convierte el texto que llego en un dict
    try:
        data = json.loads(request.body or "{}")                                            
    except json.JSONDecodeError:   
        data = None
    if not isinstance(data, dict):   
        return JsonResponse({"message": "El cuerpo debe ser JSON válido."}, status=400) 

    # reescribe el token en el formato esperado
    token = str(data.get("token") or "").strip().upper() 
    if not token:
        return JsonResponse({"message": "Falta completar el token"}, status=400)            
    try:
        repartidor = Repartidor.objects.get(token=token)
    except Repartidor.DoesNotExist:
        return JsonResponse({"message": MSG_TOKEN_INVALIDO}, status=404)


    # Escenario 3: el repartidor fue dado de baja por el coordinador
    if repartidor.estado == "baja":
        return JsonResponse({"message": MSG_REPARTIDOR_BAJA}, status=403)

    #Si el token existe devuelve todos los datos el repartidor
    return JsonResponse(                                                 
        {
            "message": "Bienvenido",
            "id": repartidor.id,
            "nombre": repartidor.nombre,
            "apellido": repartidor.apellido,
            "estado": repartidor.estado,
            "token": repartidor.token,
        }
    )

