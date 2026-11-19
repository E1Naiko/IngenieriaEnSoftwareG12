"""Login del repartidor (HU #9)"""

import json

from django.http import JsonResponse 
from django.views.decorators.csrf import csrf_exempt 
from django.views.decorators.http import require_POST
from core.estados import esta_habilitado
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


    # Escenario 3: el repartidor fue dado de baja por el coordinador.
    # core.estados.esta_habilitado normaliza el estado: también bloquea
    # 'BAJA' y variantes con espacios (HU #38).
    if not esta_habilitado(repartidor):
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



MSG_DATOS_INCORRECTOS = "Datos incorrectos"


@csrf_exempt  # el repartidor que olvidó el token no tiene sesión ni CSRF
@require_POST
def recuperar_token(request):
    """HU #29: con el DNI, genera un token nuevo y lo devuelve para mostrarlo en pantalla."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        data = None
    if not isinstance(data, dict):
        return JsonResponse({"message": "El cuerpo debe ser JSON válido."}, status=400)

    dni = str(data.get("dni") or "").strip()
    if not dni:
        return JsonResponse({"message": "Falta completar el DNI"}, status=400)
    if not dni.isdigit():
        return JsonResponse({"message": MSG_DATOS_INCORRECTOS}, status=400)

    # Escenario 2: DNI no registrado
    try:
        repartidor = Repartidor.objects.get(dni=int(dni))
    except Repartidor.DoesNotExist:
        return JsonResponse({"message": MSG_DATOS_INCORRECTOS}, status=404)

    # Igual que en el login: un repartidor dado de baja no recupera acceso
    if not esta_habilitado(repartidor):
        return JsonResponse({"message": MSG_REPARTIDOR_BAJA}, status=403)

    # Escenario 1: el token nuevo reemplaza al anterior, que deja de servir para el login
    repartidor.token = Repartidor._generar_token()
    repartidor.save(update_fields=["token"])
    return JsonResponse({"token": repartidor.token})
