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

- Desacopla el CRUD de comercios del resto del dominio (`core`, `repartidoresDisponibles`).
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
├── tests.py           # 10 tests de integración sobre la API
├── migrations/        # vacío (sin modelos propios no hay migraciones)
└── README.md          # este archivo
```

### Dependencias externas

```
crudComercios.views  →  core.models.Comercio
                     →  core.models.Cliente   (solo para validar FK datos_cliente)
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
| `datos_cliente` | `FK → Cliente` | **Opcional** (`null=True`, `SET_NULL`, `related_name="+"`). Ver § 7 sobre el ciclo |

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
  "direccion": "Calle 7 #123, La Plata",
  "datos_cliente": 4
}
```

`datos_cliente` es el **ID** del `Cliente` vinculado o `null` si no hay.

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
{ "datos_cliente": "Cliente no encontrado." }
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
| `datos_cliente` | `null`, `""` → `None`. Entero → debe existir `Cliente` con ese PK | 400 `{"datos_cliente": ...}` |

- `PUT` exige los tres campos; `PATCH` solo valida los presentes.
- Todos los valores se guardan con `strip()` para evitar espacios accidentales.
- Body vacío en POST/PUT/PATCH → `{}` (se disparan los errores de campos faltantes).
- Body no-JSON o JSON que no es objeto → `400 {"detail": "El cuerpo debe ser JSON válido."}`.

---

## 7. FK `datos_cliente` y el ciclo `comercio ↔ cliente`

El diagrama exige `comercio.id_datos_cliente → cliente` y `cliente.id_comercio → comercio`.
Si ambos fueran `NOT NULL` nadie podría crearse primero (deadlock de FK).

Decisión del proyecto (`Info/DB.md`): `Comercio.datos_cliente` es **nullable**.

Flujo válido:

```
1. POST /api/comercios/  {nombre, telefono, direccion}          → crea comercio sin cliente
2. Crear Cliente con comercio=<id>  (vía admin o API de clientes)
3. PATCH /api/comercios/<id>/ {datos_cliente: <cliente_id>}     → linkea
```

Enviar `{"datos_cliente": null}` o `{"datos_cliente": ""}` desvincula.

---

## 8. Helpers internos (`views.py`)

| Función | Firma | Rol |
|---|---|---|
| `_parse_body(request)` | `Request → dict \| None` | Decodifica `request.body` como UTF-8 JSON. Devuelve `{}` si vacío, `None` si inválido/no-dict |
| `_comercio_to_dict(comercio)` | `Comercio → dict` | Serializa a JSON (expone `datos_cliente_id`, no el objeto) |
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
| `test_datos_cliente_fk` | `PATCH {datos_cliente: id}` linkea Cliente |

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

El form envía `{nombre, telefono, direccion, datos_cliente}` con `Content-Type: application/json`.
`datos_cliente` se envía como `number | null` (el input opcional se convierte con `Number()`).

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

# PATCH (parcial + link cliente)
curl -s -X PATCH http://127.0.0.1:8000/api/comercios/1/ \
  -H "Content-Type: application/json" \
  -d '{"datos_cliente": 3}' | jq

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
