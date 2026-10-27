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

> No hay más campos ni FK en el modelo: `comercio` es una tabla de tres datos.
> Cómo se relaciona con `Cliente` → § 7.

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
| `DELETE` | `/api/comercios/<id>/` | `comercio_detail` | Borrado → `204` **sin body** |

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

Son las **únicas** cuatro claves, sin objetos anidados ni consultas extra por fila.
Cualquier otra clave que envíe el llamador se ignora en silencio (ver § 6).

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

Cualquier clave que no sea una columna del modelo se ignora: no se guarda y no devuelve `400`.

- `PUT` exige los tres campos; `PATCH` solo valida los presentes.
- Todos los valores se guardan con `strip()` para evitar espacios accidentales.
- Body vacío en POST/PUT/PATCH → `{}` (se disparan los errores de campos faltantes).
- Body no-JSON o JSON que no es objeto → `400 {"detail": "El cuerpo debe ser JSON válido."}`.

---

## 7. Comercio y cliente: dos tablas independientes

`comercio` no referencia a `cliente` ni al revés: no hay ninguna FK entre las
dos tablas. Por eso el CRUD es tan simple: no valida FK, no importa `Cliente`
y un comercio se da de alta con sus tres datos, en cualquier orden.

El par comercio ↔ cliente solo convive dentro de un `Paquete`, que guarda
`id_comercio` e `id_datos_cliente` al ingresarse el pedido (HU #37). Se consulta así:

```python
Paquete.objects.filter(comercio=comercio, cliente=cliente)   # pedidos de ese par
cliente.paquetes.values_list("comercio__nombre", flat=True)  # comercios del cliente
```

El endpoint expone exactamente lo que hay en la tabla: `nombre`, `telefono` y
`direccion` además del `id`. Agregar un campo implica tocar `core/models.py`,
generar su migración, `_comercio_to_dict()` y `_validar_y_aplicar()`.

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
- **Base de datos**: PostgreSQL en Supabase con proyectos separados para desarrollo y producción; SQLite queda como opción offline (`DATABASE_MODE=sqlite`). La tabla usada es `comercio`.

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
| `test_contrato_cuatro_claves` | la respuesta trae `id`, `nombre`, `telefono`, `direccion` y nada más |
| `test_clave_desconocida_se_ignora` | una clave que el modelo no tiene no rompe ni se guarda |

Ejecutar:

```bash
cd backend
DATABASE_MODE=sqlite python manage.py test crudComercios        # solo este módulo
DATABASE_MODE=sqlite python manage.py test crudComercios.tests.ComercioAPITests.test_listar  # uno puntual
DATABASE_MODE=sqlite python manage.py test                      # todo el proyecto
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

El form envía las tres claves del modelo —`{nombre, telefono, direccion}`— con
`Content-Type: application/json`; el `id` lo asigna la base.

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
