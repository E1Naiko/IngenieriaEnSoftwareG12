# crudComercios — CRUD de Comercios

Módulo Django que expone la **API REST para Comercios** (`Comercio` de `core`).
Es el backend que consume la página `frontend/src/pages/Comercios.tsx` y cualquier
cliente HTTP que hable JSON.

> **Ubicación:** `backend/crudComercios/`  
> **Modelo de datos:** `core.models.Comercio` (este módulo **no** define modelos propios)  
> **Rutas montadas en:** `config/urls.py → api/` + `crudComercios/urls.py`

---

## 1. Propósito

Centralizar toda la lógica de **alta, listado, detalle, edición y borrado** de comercios:

- Desacopla el CRUD de comercios del resto del dominio (`core`, `repatidoresDisponibles`).
- Mantiene dependencias mínimas: **no usa DRF**, solo `JsonResponse` + vistas funcionales.
- Define el contrato JSON que el frontend ya consume.

---

## 2. Estructura del directorio

```
crudComercios/
├── __init__.py        # marca el paquete Python
├── apps.py            # AppConfig (nombre y etiqueta de la app)
├── models.py          # vacío a propósito — ver sección 3
├── views.py           # toda la lógica del CRUD (2 vistas + 3 helpers)
├── urls.py            # 2 rutas REST
├── admin.py           # sin registro propio (Comercio se administra en core)
├── tests.py           # 12 tests de integración sobre la API
├── migrations/        # vacío (sin modelos propios no hay migraciones)
└── README.md          # este archivo
```

### Dependencias externas

```
crudComercios.views  →  core.models.Comercio
config/urls.py       →  crudComercios.urls    (include bajo /api/)
```

---

## 3. ¿Por qué `models.py` está vacío?

El diagrama de la base (`Info/DB.md`) define **un único origen de verdad** para las
tablas: `core/models.py` (`repartidor`, `comercio`, `cliente`, `paquete`, `comprobante`).

`crudComercios` **reutiliza** `core.Comercio` en lugar de duplicarlo. Esto evita:

- Tablas duplicadas / migraciones divergentes.
- Ciclos de importación.
- Tener que sincronizar dos definiciones del mismo comercio.

> Si en el futuro `Comercio` necesitara lógica exclusiva del CRUD (managers,
> querysets, signals), se evaluaría mover el modelo o crear un proxy; por ahora
> la separación por vistas es suficiente.

---

## 4. Modelo `Comercio` (referencia rápida)

Definido en `core/models.py`:

| Campo | Tipo | Notas |
|---|---|---|
| `id` | `AutoField` | PK autoincremental |
| `nombre` | `CharField(255)` | Obligatorio |
| `telefono` | `CharField(255)` | Obligatorio |
| `direccion` | `CharField(255)` | Obligatorio |

> El modelo **no** tiene más campos: el vínculo con `Cliente` salió del diagrama (ver § 7).

```python
from core.models import Comercio
Comercio.objects.create(nombre="Kiosco Central", telefono="221-555-0100", direccion="Calle 7 #123")
```

Meta: `db_table = "comercio"`, `ordering = ["nombre"]`, `verbose_name = "comercio"`.

El admin de `Comercio` ya está registrado en `core/admin.py` (`ComercioAdmin` con
`list_display` y `search_fields`).

---

## 5. Endpoints REST

Prefijo global: `/api/` (definido en `config/urls.py`).

| Método | Ruta | Vista | Descripción |
|---|---|---|---|
| `GET` | `/api/comercios/` | `comercios_list` | Listar (acepta `?q=` para filtrar por nombre) |
| `POST` | `/api/comercios/` | `comercios_list` | Crear |
| `GET` | `/api/comercios/<id>/` | `comercio_detail` | Detalle |
| `PUT` | `/api/comercios/<id>/` | `comercio_detail` | Reemplazo total (todos los campos obligatorios) |
| `PATCH` | `/api/comercios/<id>/` | `comercio_detail` | Actualización parcial (solo lo enviado) |
| `DELETE` | `/api/comercios/<id>/` | `comercio_detail` | Borrado |

> Nota: en `crudComercios/urls.py` las rutas se definen como `comercios/<int:pk>/`; en la documentación se usa `<id>` como alias genérico.

`GET /api/comercios/?q=texto` → filtra con `nombre__icontains` (búsqueda case-insensitive).

### Contrato JSON

**Comercio** serializado por `_comercio_to_dict()`:

```json
{
  "id": 1,
  "nombre": "Kiosco Central",
  "telefono": "221-555-0100",
  "direccion": "Calle 7 #123, La Plata"
}
```

Son las **únicas** claves del contrato. `datos_cliente` ya no existe (ver § 7) y, si un
cliente lo sigue enviando, se ignora en silencio — la API nunca rechazó campos extra.

**Listado:**

```json
{
  "results": [ { ... }, { ... } ],
  "count": 2
}
```

**Errores de validación** → `400` con el campo como clave:

```json
{ "nombre": "El nombre es obligatorio." }
{ "detail": "El cuerpo debe ser JSON válido." }
```

**No encontrado** → `404`:

```json
{ "detail": "Comercio no encontrado." }
```

**Método no permitido** → `405`:

```json
{ "detail": "Método no permitido." }
```

---

## 6. Validaciones

Implementadas en `_validar_y_aplicar(comercio, data, parcial)`:

| Campo | Regla | Error |
|---|---|---|
| `nombre` | `str` no vacío (tras `strip()`). Obligatorio si `parcial=False` (POST/PUT) | 400 `{"nombre": ...}` |
| `telefono` | idem | 400 `{"telefono": ...}` |
| `direccion` | idem | 400 `{"direccion": ...}` |

Claves desconocidas (incluido el `datos_cliente` del esquema viejo) se ignoran.

- `PUT` exige los tres campos; `PATCH` solo valida los presentes.
- Todos los valores se guardan con `strip()` para evitar espacios accidentales.
- Body vacío en POST/PUT/PATCH → `{}` (se disparan los errores de campos faltantes).
- Body no-JSON o JSON que no es objeto → `400 {"detail": "El cuerpo debe ser JSON válido."}`.

---

## 7. Comercio ↔ cliente: ya no hay FK directa

Hasta el 20/10 el diagrama tenía `comercio.id_datos_cliente → cliente` y
`cliente.id_comercio → comercio`. Como ambos eran `NOT NULL`, nadie podía
crearse primero (deadlock de FK) y el proyecto lo había resuelto con un
`datos_cliente` **nullable**.

**Scrum 23/10 (HU #37 "Ingresar pedido"): se quitó el vínculo de la base.**
Los modelos ya no tienen ninguna de las dos FK, así que:

- Un comercio y un cliente se crean de forma independiente y en cualquier orden.
- Qué clientes atiende un comercio (y viceversa) se infiere por `Paquete`,
  que guarda `id_comercio` e `id_datos_cliente`:

```python
Paquete.objects.filter(comercio=comercio, cliente=cliente)   # pedidos de ese par
cliente.paquetes.values_list("comercio__nombre", flat=True)  # comercios del cliente
```

El endpoint `/api/comercios/` por lo tanto serializa y valida solo
`nombre`, `telefono` y `direccion`. El campo `datos_cliente` se sigue
ignorando si llega, para no romper llamadores viejos.

---

## 8. Helpers internos (`views.py`)

| Función | Firma | Rol |
|---|---|---|
| `_parse_body(request)` | `Request → dict \| None` | Decodifica `request.body` como UTF-8 JSON. Devuelve `{}` si vacío, `None` si inválido/no-dict |
| `_comercio_to_dict(comercio)` | `Comercio → dict` | Serializa a JSON (`id`, `nombre`, `telefono`, `direccion`) |
| `_validar_y_aplicar(comercio, data, parcial)` | `(Comercio, dict, bool) → (bool, JsonResponse\|None)` | Valida y muta **en memoria** el objeto; no guarda. Devuelve `(True, None)` o `(False, error_response)` |

Las vistas solo llaman a `comercio.save()` / `comercio.delete()` si la validación pasó.

---

## 9. Seguridad y configuración

- **`@csrf_exempt`**: necesario porque el frontend React envía JSON sin token CSRF. Si se migra a sesión/cookies, quitar el decorador y enviar `X-CSRFToken`.
- **`@require_http_methods`** no se usa explícitamente: cada vista comprueba `request.method` y devuelve `405` para verbos no soportados.
- **CORS / Hosts**: `config/settings.py` lista `http://localhost:5173` (Vite) en `CORS_ALLOWED_ORIGINS`; con `DEBUG=True`, `ALLOWED_HOSTS = ["*"]` acepta cualquier host/preview `*.e2b.app`. Para más orígenes CORS completar `CORS_ALLOWED_ORIGINS` / `DJANGO_ALLOWED_HOSTS`.
- **Base de datos**: PostgreSQL (Supabase) vía `.env`; fallback a `db.sqlite3` si `DB_HOST` vacío. La tabla usada es `comercio`.

---

## 10. Tests (`tests.py`)

Suite de integración con `django.test.TestCase` (`ComercioAPITests`):

| Test | Qué verifica |
|---|---|
| `test_listar` | `GET /api/comercios/` → 200, `count` y contenido |
| `test_crear` | `POST` válido → 201 y crea en BD |
| `test_crear_faltan_campos` | `POST` incompleto → 400 |
| `test_detalle` | `GET /api/comercios/<id>/` → 200 |
| `test_detalle_404` | `GET` ID inexistente → 404 |
| `test_actualizar_put` | `PUT` reemplaza todos los campos |
| `test_actualizar_patch` | `PATCH` parcial mantiene no enviados |
| `test_borrar` | `DELETE` → 204 y borra |
| `test_filtro_q` | `GET ?q=Otro` filtra por `nombre` |
| `test_sin_datos_cliente_en_el_contrato` | la respuesta trae solo las 4 claves del esquema nuevo |
| `test_datos_cliente_se_ignora` | `PATCH {datos_cliente: ...}` no rompe: se ignora |
| `test_cliente_se_crea_sin_comercio` | `Cliente` se da de alto sin comercio (FK eliminada) |

Ejecutar:

```bash
cd backend
python manage.py test crudComercios        # solo este módulo
python manage.py test crudComercios.tests.ComercioAPITests.test_listar  # uno puntual
python manage.py test                      # todo el proyecto
```

---

## 11. Uso desde el frontend

`frontend/src/pages/Comercios.tsx` ya consume estos endpoints:

```ts
GET    /api/comercios/          → carga tabla
GET    /api/comercios/?q=...    → (disponible, aún no usado en la UI)
POST   /api/comercios/          → crear desde el form (modo creación)
PUT    /api/comercios/<id>/     → guardar edición
DELETE /api/comercios/<id>/     → botón Eliminar
```

El form envía `{nombre, telefono, direccion}` con `Content-Type: application/json`
(salen las claves del vínculo con cliente que existía antes del cambio de esquema).

Si el backend devuelve `4xx/5xx`, la UI muestra `JSON.stringify(data)` en rojo.

---

## 12. Ejemplos `curl`

```bash
# Listar
curl -s http://127.0.0.1:8000/api/comercios/ | jq

# Filtrar
curl -s "http://127.0.0.1:8000/api/comercios/?q=kiosco" | jq

# Crear
curl -s -X POST http://127.0.0.1:8000/api/comercios/ \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Kiosco Central","telefono":"221-555-0100","direccion":"Calle 7 #123"}' | jq

# Detalle
curl -s http://127.0.0.1:8000/api/comercios/1/ | jq

# PUT (reemplazo total)
curl -s -X PUT http://127.0.0.1:8000/api/comercios/1/ \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Kiosco Editado","telefono":"221-999-0000","direccion":"Calle 8 #456"}' | jq

# PATCH (parcial)
curl -s -X PATCH http://127.0.0.1:8000/api/comercios/1/ \
  -H "Content-Type: application/json" \
  -d '{"telefono": "221-999-0000"}' | jq

# DELETE
curl -s -X DELETE http://127.0.0.1:8000/api/comercios/1/ -i
```

---

## 13. Cómo extender

- **Validaciones nuevas** (p. ej. formato de teléfono): agregar rama en `_validar_y_aplicar()`.
- **Nuevo campo en Comercio**: agregar columna en `core/models.py`, `makemigrations`, exponer en `_comercio_to_dict()` y validar en `_validar_y_aplicar()`.
- **Paginación**: reemplazar `qs` por `Paginator` en `comercios_list` manteniendo `{results, count}`.
- **DRF**: si el proyecto migra, reescribir las vistas como `ModelViewSet` manteniendo rutas y contratos.
- **Autenticación**: envolver vistas con `@login_required` o JWT y quitar `csrf_exempt`.

---

## 14. Referencias

- Modelo y decisiones de esquema: `Info/DB.md`
- Configuración y CORS: `config/settings.py`
- Montaje de rutas: `config/urls.py`
- Admin de Comercio: `core/admin.py`
- UI: `frontend/src/pages/Comercios.tsx`
