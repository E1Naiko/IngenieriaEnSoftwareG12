# loginCoordinador — Inicio de sesión del coordinador (HU #4)

Endpoint para que el **coordinador** entre al sistema con usuario y contraseña.
El login del repartidor (por token, HU #9) es otro flujo y no pasa por acá.

> **Ubicación:** `backend/loginCoordinador/`
> **Modelo de datos:** el `User` que ya trae Django (`django.contrib.auth`). No hay modelos ni migraciones propias.
> **Ruta:** `POST /api/login-coordinador/` (montada en `config/urls.py → api/`)

---

## 1. Contrato de la API

```
POST /api/login-coordinador/
Content-Type: application/json

{"username": "coordinador", "password": "****"}
```

| Caso (escenario de la HU #4) | Código | Respuesta |
|---|---|---|
| 1. Usuario y contraseña correctos | `200` | `{"message": "Bienvenido"}` + cookie `sessionid` |
| 2. Falta el usuario o la contraseña | `400` | `{"message": "Falta completar uno o más campos"}` |
| 3. Usuario inexistente o contraseña incorrecta | `401` | `{"message": "Usuario no encontrado, o contraseña incorrecta. Por favor verificar datos ingresados"}` |
| Usuario desactivado (`is_active = False`) | `401` | mismo mensaje que el caso 3 |
| El cuerpo no es JSON | `400` | `{"message": "El cuerpo debe ser JSON válido."}` |
| Cualquier método que no sea `POST` | `405` | sin cuerpo |

- Los mensajes son los textos exactos de la HU, así que el front puede mostrar `data.message` directamente.
- En `curl` las tildes aparecen como `á`: es el escape estándar de JSON. `response.json()` en el front las muestra bien.
- Usuario inexistente y contraseña incorrecta devuelven **el mismo mensaje** a propósito: así no se puede averiguar qué usuarios existen.

---

## 2. Cómo funciona

1. Lee el JSON del cuerpo y valida que vengan los dos campos. La validación también está en el back porque la API se puede llamar sin pasar por el front.
2. `authenticate()` de Django compara contra la contraseña guardada cifrada y rechaza usuarios desactivados.
3. Si es válido, `login()` crea la **sesión de Django**: el navegador recibe la cookie `sessionid` y la manda sola en los pedidos siguientes.

### Decisiones

- **Coordinador = usuario de Django.** El coordinador es único; se crea una sola vez (ver sección 4). No hace falta un modelo propio.
- **Sesión de Django, no token.** El token es del login de repartidores (HU #9). Para el coordinador alcanza con la sesión que Django ya trae.
- **`@csrf_exempt`**, igual que `crudComercios`: antes de iniciar sesión el front no tiene token CSRF.
- **Ruta bajo `/api/`:** el proxy de Vite solo reenvía a Django lo que empieza con `/api`. Así el front llama a `/api/login-coordinador/` (ruta relativa), sin CORS, y la cookie de sesión queda en el mismo sitio.

---

## 3. Estructura

```
loginCoordinador/
├── __init__.py
├── apps.py        # AppConfig
├── views.py       # vista login_coordinador
├── urls.py        # ruta login-coordinador/
├── tests.py       # 6 tests (escenarios de la HU + bordes)
└── README.md      # este archivo
```

Cambios fuera de la app: `"loginCoordinador"` en `INSTALLED_APPS` (`config/settings.py`) y `path("api/", include("loginCoordinador.urls"))` en `config/urls.py`.

---

## 4. Crear el coordinador

Una sola vez por base de datos:

```bash
cd backend
python manage.py createsuperuser   # usuario, mail (opcional) y contraseña
```

Ese usuario también entra a `/admin/`. Si se crea con el `.env` de Supabase, queda en la base compartida del equipo.

---

## 5. Probar

```bash
python manage.py test loginCoordinador
```

A mano, con `runserver` levantado:

```bash
curl -i -X POST http://127.0.0.1:8000/api/login-coordinador/ \
  -H "Content-Type: application/json" \
  -d '{"username":"coordinador","password":"TU_CLAVE"}'
```

---

## 6. Qué tiene que hacer el front

En `frontend/src/components/login/login.tsx`, cambiar la URL del `fetch`:

```diff
- "http://127.0.0.1:8000/login/",
+ "/api/login-coordinador/",
```

Con la ruta relativa el pedido pasa por el proxy de Vite. Lo demás (enviar `username` y `password`, leer `data.message`) ya coincide con el contrato.

---
