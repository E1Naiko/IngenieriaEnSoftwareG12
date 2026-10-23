# CRUD — Qué es, para qué sirve y cómo está implementado en este proyecto

> **Ubicación del código:** `backend/crudComercios/` (API) + `frontend/src/pages/Comercios.tsx` (UI)  
> **Modelo:** `backend/core/models.py → Comercio`  
> **Documentación técnica detallada:** `backend/crudComercios/README.md`  
> **Esquema de BD:** `Info/DB.md`

---

## 1. ¿Qué es un CRUD?

**CRUD** es el acrónimo de las cuatro operaciones básicas que toda aplicación que guarda datos necesita hacer sobre sus entidades:

| Sigla | Operación | Verbo HTTP | SQL | Qué hace |
|-------|-----------|------------|-----|----------|
| **C** | **Create** | `POST` | `INSERT` | Crea un registro nuevo |
| **R** | **Read** | `GET` | `SELECT` | Lee / lista registros |
| **U** | **Update** | `PUT` / `PATCH` | `UPDATE` | Modifica un registro |
| **D** | **Delete** | `DELETE` | `DELETE` | Elimina un registro |

Es un patrón tan común que casi todo framework lo reconoce y ofrece atajos para generarlo
(formularios admin, scaffolding, `ModelViewSet` en DRF, etc.).

Un CRUD **no es un tipo de base de datos** ni un lenguaje: es una **forma de organizar**
las operaciones sobre datos persistentes. Cualquier entidad del sistema (un comercio,
un usuario, un paquete) puede tener su propio CRUD.

### CRUD vs. REST vs. API

- **CRUD**: qué operaciones existen (concepto).
- **REST**: cómo se exponen esas operaciones por HTTP (convención de URLs y verbos).
- **API**: la implementación concreta (código que responde a esas URLs).

En este proyecto el CRUD de Comercios se expone como **API REST** con URLs como `/api/comercios/`.

---

## 2. ¿Para qué sirve?

Un CRUD resuelve el problema central de cualquier sistema de gestión:

1. **Dar de alta información** — sin CRUD no hay forma de cargar datos.
2. **Consultar** — listar, buscar, filtrar y ver el detalle de lo guardado.
3. **Mantener actualizado** — corregir errores, cambiar teléfono/dirección, vincular relaciones.
4. **Limpiar** — borrar lo que ya no corresponde (comercios cerrados, datos de prueba).

Sin un CRUD, la única alternativa sería editar la base de datos a mano (con `psql`, `sqlite3`
o el panel de Supabase), lo cual es lento, propenso a errores y no escalable.

### En el contexto de este sistema

Este proyecto es un **sistema de reparto de paquetes**. Los **comercios** son uno de los
actores principales: son quienes despachan paquetes. Necesitamos:

- Registrar nuevos comercios cuando se asocian al servicio.
- Listar y buscar comercios para asignarles paquetes.
- Editar sus datos (cambio de teléfono, dirección, persona de contacto).
- Eliminar comercios inactivos.

Todo eso es exactamente lo que implementa `crudComercios`. Otros CRUD del sistema
(repartidores, clientes, paquetes) siguen el mismo patrón pero viven en sus propias
apps (`repatidoresDisponibles`, etc.).

---

## 3. Cómo está implementado en este proyecto

### 3.1. Arquitectura general

```
┌──────────────┐      HTTP JSON       ┌─────────────────────────┐      ORM      ┌────────────┐
│   Frontend   │  ───────────────►    │  backend/crudComercios  │  ─────────►  │ PostgreSQL │
│  React SPA   │  ◄───────────────    │  (vistas + validación)  │  ◄─────────  │ (Supabase) │
│ Comercios.tsx│                      │  usa core.Comercio      │              │ tabla      │
└──────────────┘                      └─────────────────────────┘              │ comercio   │
                                         ▲                                     └────────────┘
                                         │ montado en
                                         │ config/urls.py → /api/
```

Decisiones clave:

- **Sin Django REST Framework**: las vistas usan solo `JsonResponse` y `json.loads()` para mantener
  dependencias mínimas. Si el proyecto crece, migrar a DRF es trivial porque el contrato JSON ya existe.
- **App separada `crudComercios`**: desacopla la lógica de comercios del resto (`core`,
  `repatidoresDisponibles`). Cada CRUD puede evolucionar sin tocar los otros.
- **Modelo en `core`**: `Comercio` vive en `core/models.py` (fuente única de verdad, `db_table = "comercio"`).
  `crudComercios/models.py` está intencionalmente vacío — ver `backend/crudComercios/README.md §3`.

### 3.2. Estructura de archivos

```
backend/crudComercios/
├── __init__.py        # marca el paquete Python
├── apps.py            # AppConfig (registrada en INSTALLED_APPS)
├── models.py          # vacío — el modelo está en core.models.Comercio
├── views.py           # corazón del CRUD: 2 vistas + 3 helpers
├── urls.py            # 2 rutas REST montadas bajo /api/
├── admin.py           # vacío — Comercio se administra en core/admin.py
├── tests.py           # 12 tests de integración
├── migrations/        # vacío (sin modelos propios)
└── README.md          # documentación técnica exhaustiva
```

Dependencias:

```
crudComercios.views  →  core.models.Comercio  (única dependencia: el CRUD ya no valida FK)
config/urls.py       →  crudComercios.urls    (include "/api/")
```

### 3.3. Modelo `Comercio`

Definido en `core/models.py`:

| Campo | Tipo Django | BD | Notas |
|-------|-------------|----|-------|
| `id` | `AutoField` | `integer PK` | Autoincremental |
| `nombre` | `CharField(255)` | `varchar(255)` | Obligatorio |
| `telefono` | `CharField(255)` | `varchar(255)` | Obligatorio |
| `direccion` | `CharField(255)` | `varchar(255)` | Obligatorio |

Meta: `db_table = "comercio"`, `ordering = ["nombre"]`.

> **Comercio ↔ cliente:** no hay FK entre las dos tablas, así que el CRUD no valida FK ni
> necesita importar `Cliente`: un comercio se crea con sus tres datos, en cualquier orden.
> El par comercio-cliente solo convive en `Paquete`, que apunta a ambos. Ver `Info/DB.md` y
> `backend/crudComercios/README.md §7`.

### 3.4. Endpoints REST

Prefijo global `/api/` definido en `config/urls.py`.

| # | Método | Ruta | Vista | Operación CRUD | Descripción |
|---|--------|------|-------|----------------|-------------|
| 1 | `GET` | `/api/comercios/` | `comercios_list` | **Read** (lista) | Lista todos; `?q=texto` filtra por `nombre__icontains` |
| 2 | `POST` | `/api/comercios/` | `comercios_list` | **Create** | Crea un comercio |
| 3 | `GET` | `/api/comercios/<id>/` | `comercio_detail` | **Read** (detalle) | Devuelve uno por PK |
| 4 | `PUT` | `/api/comercios/<id>/` | `comercio_detail` | **Update** (total) | Reemplaza: exige `nombre`, `telefono`, `direccion` |
| 5 | `PATCH` | `/api/comercios/<id>/` | `comercio_detail` | **Update** (parcial) | Solo valida los campos enviados |
| 6 | `DELETE` | `/api/comercios/<id>/` | `comercio_detail` | **Delete** | Borra → `204` sin body |

> Nota: las rutas Django se definen como `comercios/<int:pk>/`; en la tabla se usa `<id>` como alias genérico del PK.

#### Contrato JSON

Objeto comercio (producido por `_comercio_to_dict`):

```json
{
  "id": 1,
  "nombre": "Kiosco Central",
  "telefono": "221-555-0100",
  "direccion": "Calle 7 #123, La Plata"
}
```

- Son las **únicas 4 claves** del contrato: `datos_cliente` se borró del esquema y hoy se ignora si llega.
- Listado responde `{"results": [...], "count": N}`.
- Errores de validación → `400` con la clave del campo: `{"nombre": "El nombre es obligatorio."}`
- No encontrado → `404 {"detail": "Comercio no encontrado."}`
- Body no-JSON o JSON que no es objeto (lista/número) → `400 {"detail": "El cuerpo debe ser JSON válido."}`
- Método no permitido → `405 {"detail": "Método no permitido."}`.

### 3.5. Lógica interna (`views.py`)

Dos vistas funcionales + tres helpers:

| Función | Rol |
|---------|-----|
| `_parse_body(request)` | Decodifica `request.body` como JSON UTF-8. Devuelve `{}`, `None` o `dict` |
| `_comercio_to_dict(comercio)` | Serializa `Comercio` a `dict` JSON (`id`, `nombre`, `telefono`, `direccion`) |
| `_validar_y_aplicar(comercio, data, parcial)` | Valida y muta en memoria; retorna `(True, None)` o `(False, JsonResponse 400)` |
| `comercios_list(request)` | `GET` lista/filtra, `POST` crea (201), delega validación |
| `comercio_detail(request, pk)` | `GET`/`PUT`/`PATCH`/`DELETE` sobre un ID, con 404 si no existe |

Validaciones (`_validar_y_aplicar`):

- `nombre`, `telefono`, `direccion` → `str` no vacío tras `strip()`. Obligatorios en `POST`/`PUT`, opcionales en `PATCH`.
- Cualquier otra clave (incluido el extinto `datos_cliente`) se ignora en silencio, como siempre.

Las vistas solo llaman `comercio.save()` / `comercio.delete()` si la validación pasó.

### 3.6. Frontend

`frontend/src/pages/Comercios.tsx`:

- `GET /api/comercios/` al montar → tabla con ID, nombre, teléfono y dirección.
- Form con `nombre`, `telefono`, `direccion` → `POST` (crear) o `PUT` (editar).
- Botones **Editar** (carga form) y **Eliminar** (`DELETE` con `confirm`).
- Errores `400` se muestran con `JSON.stringify(data)` en rojo.

El frontend usa `fetch` con `Content-Type: application/json` y rutas relativas (`/api/...`),
que Vite proxifica al backend (ver §3.8).

### 3.7. Tests

`backend/crudComercios/tests.py` — `ComercioAPITests` (10 tests, `django.test.TestCase`):

| Test | Verifica |
|------|----------|
| `test_listar` | `GET` lista → 200, `count`/`results` |
| `test_crear` | `POST` válido → 201 y persiste |
| `test_crear_faltan_campos` | `POST` incompleto → 400 |
| `test_detalle` | `GET <id>` → 200 |
| `test_detalle_404` | `GET` inexistente → 404 |
| `test_actualizar_put` | `PUT` total → 200 y guarda |
| `test_actualizar_patch` | `PATCH` parcial → solo cambia lo enviado |
| `test_borrar` | `DELETE` → 204 y elimina |
| `test_filtro_q` | `?q=` filtra por nombre |
| `test_sin_datos_cliente_en_el_contrato` | la respuesta trae solo las 4 claves del esquema nuevo |
| `test_datos_cliente_se_ignora` | `PATCH {datos_cliente: ...}` no rompe: se ignora |
| `test_cliente_se_crea_sin_comercio` | `Cliente` ya no exige `comercio` |

Ejecutar:

```bash
cd backend
python manage.py test crudComercios -v 2
```

### 3.8. Infraestructura

- **Base de datos**: PostgreSQL en Supabase (credenciales en `backend/.env`); fallback a `db.sqlite3` si `DB_HOST` vacío.
- **CORS / Hosts** (`config/settings.py`): `CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]` (Vite); con `DEBUG=True`, `ALLOWED_HOSTS = ["*"]` acepta cualquier host/preview `*.e2b.app`. Para más orígenes completar `CORS_ALLOWED_ORIGINS` / `DJANGO_ALLOWED_HOSTS`.
- **CSRF**: vistas con `@csrf_exempt` porque el frontend envía JSON sin token. Si se usa sesión, quitar el decorador.
- **Admin**: `core/admin.py → ComercioAdmin` (`list_display`, `search_fields`). No hay `ModelAdmin` en `crudComercios`.

---

## 4. Ejemplos de uso

### cURL

```bash
# Listar
curl -s http://127.0.0.1:8000/api/comercios/ | jq

# Filtrar por nombre
curl -s "http://127.0.0.1:8000/api/comercios/?q=kiosco" | jq

# Crear
curl -s -X POST http://127.0.0.1:8000/api/comercios/ \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Kiosco Central","telefono":"221-555-0100","direccion":"Calle 7 #123"}' | jq

# Detalle
curl -s http://127.0.0.1:8000/api/comercios/1/ | jq

# Actualización total
curl -s -X PUT http://127.0.0.1:8000/api/comercios/1/ \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Kiosco Editado","telefono":"221-999-0000","direccion":"Calle 8 #456"}' | jq

# Actualización parcial — cambiar un dato
curl -s -X PATCH http://127.0.0.1:8000/api/comercios/1/ \
  -H "Content-Type: application/json" \
  -d '{"telefono": "221-999-0000"}' | jq

# Borrar
curl -s -X DELETE http://127.0.0.1:8000/api/comercios/1/ -i
```

### Python (cliente)

```python
import requests

BASE = "http://127.0.0.1:8000/api/comercios/"

# Create
r = requests.post(BASE, json={"nombre": "Kiosco", "telefono": "123", "direccion": "Calle 1"})
print(r.status_code, r.json())  # 201

# Read lista
r = requests.get(BASE, params={"q": "kiosco"})
print(r.json())  # {"results": [...], "count": ...}

# Update parcial
r = requests.patch(f"{BASE}{r.json()['results'][0]['id']}/", json={"telefono": "999"})
print(r.status_code)  # 200

# Delete
r = requests.delete(f"{BASE}1/")
print(r.status_code)  # 204
```

---

## 5. Buenas prácticas aplicadas y cómo extender

- **Validación centralizada** en `_validar_y_aplicar` — agregar un campo nuevo es una sola rama.
- **Diferencia PUT vs PATCH** explícita con `parcial` — evita confusión entre reemplazo total y parcial.
- **`strip()` sistemático** — evita datos con espacios accidentales.
- **Sin duplicar el modelo** — una sola tabla, una sola migración.
- **Sin anidados** — el contrato espeja la tabla `comercio` (4 columnas) y nada más.

Ideas para extender:

| Necesidad | Cómo hacerlo |
|-----------|-------------|
| Validar formato de teléfono | Nueva rama en `_validar_y_aplicar` (regex) |
| Nuevo campo (ej. `email`) | Columna en `core/models.py` → `makemigrations` → exponer en `_comercio_to_dict` y validar |
| Paginación | `Paginator` en `comercios_list` manteniendo `{results, count}` |
| Migración a DRF | Reescribir vistas como `ModelViewSet`, mantener rutas y contratos |
| Autenticación | Decorar vistas con `@login_required`/JWT y quitar `csrf_exempt` |
| Bulk create / import CSV | `POST /api/comercios/bulk/` con transacción atómica |

---

## 6. Referencias

- Código del CRUD: `backend/crudComercios/` (vistas, URLs, tests)
- Documentación técnica: `backend/crudComercios/README.md`
- Modelos y decisiones de esquema: `Info/DB.md`
- Configuración Django: `config/settings.py`, `config/urls.py`, `Doc de Django.md`
- UI del CRUD: `frontend/src/pages/Comercios.tsx`
- Puesta en marcha: `README.md`, `backend/README.md`

> En resumen: **CRUD = Create, Read, Update, Delete**. Es el patrón básico para gestionar datos.
> En este proyecto está implementado como una API REST en `crudComercios` que el frontend
> React consume, con modelo en `core`, validaciones explícitas, tests y documentación.