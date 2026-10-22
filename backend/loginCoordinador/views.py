"""Login del coordinador (HU #4): usuario y contraseña, con la sesión de Django."""

import json

from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# Textos exactos que pide la HU #4 en sus escenarios 2 y 3.
MSG_FALTAN_CAMPOS = "Falta completar uno o más campos"
MSG_CREDENCIALES = (
    "Usuario no encontrado, o contraseña incorrecta. "
    "Por favor verificar datos ingresados"
)


@csrf_exempt  # antes de iniciar sesión el front no tiene token CSRF
@require_POST  # cualquier otro método responde 405
def login_coordinador(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        data = None
    if not isinstance(data, dict):
        return JsonResponse({"message": "El cuerpo debe ser JSON válido."}, status=400)

    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")
    # Se valida acá aunque el front también lo haga: la API se puede llamar sin el front.
    if not username or not password:
        return JsonResponse({"message": MSG_FALTAN_CAMPOS}, status=400)

    # authenticate compara contra la contraseña cifrada y rechaza usuarios desactivados.
    # El mismo mensaje para usuario inexistente o clave mal: no revela qué usuarios existen.
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"message": MSG_CREDENCIALES}, status=401)

    login(request, user)  # crea la sesión; el navegador recibe la cookie
    return JsonResponse({"message": "Bienvenido"})
