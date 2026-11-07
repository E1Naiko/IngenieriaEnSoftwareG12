# AGENTS.md — Guía para agentes de código

Sistema de gestión de reparto de paquetes (SRFR, Grupo 12): backend **Django 5.2**
en `backend/` + frontend **React 19 + TypeScript + Vite** en `frontend/`, con
PostgreSQL/Supabase (un proyecto para desarrollo y otro para producción) y
SQLite como alternativa offline.

Todo el repo (código, comentarios, docs y commits) está **en español**. Mantener
ese idioma y ese tono en lo que se agregue.

## Comandos

Todos los comandos de Django corren **desde `backend/`** (ahí está `manage.py`).

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt                # incluye requirements.txt
cp .env.example .env                               # credenciales del Supabase de DESARROLLO
```

Verificación (es lo mismo que corre CI, job `test`):

```bash
DATABASE_MODE=sqlite DJANGO_DEBUG=True python manage.py check
DATABASE_MODE=sqlite DJANGO_DEBUG=True python manage.py makemigrations --check --dry-run
DATABASE_MODE=sqlite DJANGO_DEBUG=True python manage.py test            # suite completa
DATABASE_MODE=sqlite DJANGO_DEBUG=True python manage.py test crudComercios           # un módulo
DATABASE_MODE=sqlite DJANGO_DEBUG=True python manage.py test paquetesEnCurso.tests.PaquetesEnCursoAPITests.test_sin_paquetes_activos_devuelve_lista_vacia_y_mensaje  # un test
pyrefly check --preset default core/models.py       # tipos de los modelos
```

Con esas variables de entorno la suite da **113 tests** y tarda ~5 s.

### Frontend

```bash
cd frontend
npm ci            # o npm install; ver la nota sobre package-lock.json
npm run dev       # Vite en :5173, proxifica /api → http://127.0.0.1:8000
npm run build     # tsc -b && vite build
npm run lint      # oxlint
```

### Docker (opcional)

```bash
docker compose up --build     # lee backend/.env y ejecuta migrate al iniciar
```

## Estado actual de la suite (verificado)

Con `DATABASE_MODE=sqlite` en el commit base de esta rama:

- `manage.py check` → *System check identified no issues*.
- `manage.py makemigrations --check --dry-run` → *No changes detected*.
- `pyrefly check --preset default core/models.py` → *0 errors* **con el venv
  activado**; sin activarlo reporta 3 `missing-import` porque no encuentra
  Django en el intérprete.
- `manage.py test` → **113 tests, 2 fallos**:
  `config.tests.CableadoDeAppsTests.test_toda_app_con_urls_esta_en_installed_apps`
  falla para `paquetesEnCurso` y para `repartidoresDisponibles`. Ambas apps
  tienen `urls.py` montado en `config/urls.py` pero no figuran en
  `INSTALLED_APPS` (`config/settings.py`). Se verificó que agregar esas dos
  entradas deja la suite en `OK` (113 tests). Si se toca el cableado de apps,
  ese es el punto de partida; no asumir que la suite está verde.
- `npm run build` → OK (45 módulos, sin errores de `tsc`).
- `npm run lint` → *4 warnings y 0 errores* (`react/set-state-in-effect` en
  `AltaRepartidor.tsx`, `Comercios.tsx`, `Flota.tsx` y `PaquetesEnCurso.tsx`;
  son warnings, no bloquean).

## Reglas del backend

### La base y el entorno

- **Nunca** correr `manage.py test` sin `DATABASE_MODE=sqlite` si el `.env`
  apunta a Supabase: en modo `postgres` Django intenta crear `test_postgres` en
  el proyecto real (el README de `backend/` describe ese problema). Con
  `DATABASE_MODE=sqlite` la base de pruebas es SQLite en memoria y no se toca
  Supabase.
- `config/settings.py` **no** define un bloque `TEST`: el SQLite en memoria
  durante los tests es el comportamiento por defecto de Django, no una
  configuración del proyecto.
- Sin `DATABASE_MODE`: `DEBUG=True` → SQLite; `DEBUG=False` → PostgreSQL **sin
  fallback** (credenciales incompletas o de plantilla `<...>` abortan el
  arranque con `ImproperlyConfigured`).
- `python manage.py revisar_db` es de solo lectura: dice a qué host/motor se va
  a conectar, qué cambios de modelo faltan migrar y cuántas filas tiene cada
  tabla. Usarlo **antes** de cualquier `migrate` o `DROP`.
- Son dos proyectos Supabase distintos (desarrollo y producción). Las
  credenciales de producción no van al `.env` local ni a la imagen Docker;
  `backend/.env.supabase.example` es solo plantilla.
- Los `DROP TABLE` / `DROP SCHEMA` documentados en `backend/README.md` son solo
  para desarrollo y después de confirmar el host. `cargar_repartidores_demo`
  requiere `--confirmar-desarrollo` y no se ejecuta en producción.

### Modelo de datos

- `core/models.py` es la **única fuente de verdad**: las tablas `repartidor`,
  `comercio`, `cliente`, `paquete` y `comprobante` (nombres del diagrama vía
  `Meta.db_table`). Las demás apps tienen `models.py` vacío a propósito; no
  duplicar modelos ni crear proxies sin discutirlo.
- `paquete.tamanio_nivel` y `repartidor.tamanio_maximo_nivel` son
  `GeneratedField` con `db_persist=True`: las calcula la base. **No
  escribirlas** a mano y usar `refresh_from_db()` después de un `save()` para
  leer el valor nuevo. Comparar niveles con el ORM
  (`tamanio_maximo_nivel__gte=paquete.tamanio_nivel`), no con los strings.
- `Repartidor.token` (6 caracteres) y `Paquete.cod_seguimiento`
  (`SRFR-XXXXXXXX`) se autogeneran en `save()`; no los asigna la vista.
- Los `choices` validan en formularios, admin y `full_clean()`, pero `save()` y
  `objects.create()` **no** llaman a `full_clean()`, y el esquema no tiene
  `CHECK`: SQL directo o `.update()` pueden escribir cualquier valor.
- Si cambia `models.py`: `python manage.py makemigrations core` y después
  `migrate`. CI corre `makemigrations --check --dry-run`, así que una
  migración faltante rompe la build. No editar migraciones ya aplicadas: se
  agrega una nueva (ver `core/migrations/0008_*` y `0009_*`, que corrigen datos
  en vez de reescribir la anterior).

### Endpoints nuevos

Para agregar una ruta hay **tres** puntos que deben coincidir, y
`config/tests.py` los verifica uno por uno:

1. `<app>/urls.py` con los `path(...)` y su `name` (para `reverse()`).
2. `path("api/", include("<app>.urls"))` en `config/urls.py`.
3. `"<app>"` en `INSTALLED_APPS` (`config/settings.py`).

Todo se monta bajo `/api/`. Los `reverse()` de cada `name` también se prueban.

### Estilo de la API

- **Sin Django REST Framework**: vistas funcionales + `JsonResponse` +
  `json.loads`, con `@csrf_exempt` (el front manda JSON sin token CSRF) y
  `@require_POST` / `@require_http_methods`.
- Errores: `400` con `{campo: mensaje}` (pueden venir varios campos a la vez),
  `{"detail": "..."}` o `{"message": "..."}` para errores genéricos, `404` si
  no existe, `405` sin cuerpo para verbos no soportados.
- Helpers con `_` al inicio por app: `_parse_body` está en `crudComercios`,
  `crudRepartidor` e `ingresarPedido`; el serializador `_<entidad>_to_dict`
  también en `paquetesEnCurso` y `repartidoresDisponibles`. Las apps de login
  y `actualizacionEstado` parsean el JSON en la propia vista: mantener el
  estilo del archivo que se está tocando.
- Varios mensajes son el texto literal de la historia de usuario y hay tests
  que los comparan palabra por palabra. En `actualizacionEstado/tests.py` y
  `loginRepartidor/tests.py` los strings están repetidos en el test, así que
  cambiar el texto de la vista rompe la suite; en `crudRepartidor` y
  `loginCoordinador` el test importa la constante `MSG_*` de `views.py` (ahí
  conviene seguir ese patrón en vez de duplicar el literal).
- Tres apps documentan su contrato JSON y su tabla de tests en su propio
  README: `crudComercios/README.md`, `crudRepartidor/README.md` y
  `loginCoordinador/README.md`. Leerlo antes de tocar la app y actualizarlo si
  cambia el contrato; el resto de las apps se documentan en `README.md` de la
  raíz de `backend/` y en `Info/`.

## Reglas del frontend

- El front llama con **rutas relativas** (`/api/...`) y el `server.proxy` de
  `vite.config.ts` las reenvía a `http://127.0.0.1:8000`; así son mismo origen
  y la cookie de sesión viaja sola. **Excepciones actuales**:
  `src/components/loginRepartidor/LoginRepartidor.tsx` y
  `src/pages/AltaRepartidor.tsx` tienen `http://127.0.0.1:8000/api`
  hardcodeado, lo que rompe si el front no corre en la máquina del backend.
  No agregar más URLs absolutas.
- Rutas en `src/App.tsx`, páginas en `src/pages/`, componentes en
  `src/components/`, CSS por página en `src/styles/`.
- `npm install` puede reescribir `frontend/package-lock.json` (por ejemplo
  borrando los campos `libc` de los paquetes opcionales según la versión de
  npm). Revisar el `git diff` del lockfile antes de commitear: si cambió solo
  por la versión de npm y no cambió `package.json`, descartarlo.

## CI y publicación

`.github/workflows/docker-hub.yml` corre en **cualquier** push y en todos los
PR:

- Job `test`: `manage.py check`, `pyrefly`, `makemigrations --check --dry-run`
  y `manage.py test`, siempre con `DATABASE_MODE=sqlite`.
- Job `build`: construye la imagen, corre `manage.py check` adentro y consulta
  `/api/ping/`.
- Publicación en Docker Hub: automática solo en `main` (`latest` y
  `main-<sha7>`). En otras ramas hay que pedirla con `[publicar-imagen]` en el
  mensaje del commit, con `DOCKERHUB_PUBLISH_DEV=true` o con *Run workflow*;
  publica `dev-<rama>-<sha7>` y nunca toca `latest`. Los PR jamás publican.

## Convenciones

- Identificadores, docstrings, comentarios, docs y commits **en español**.
- No commitear `.env` ni credenciales: `.gitignore` ignora `.env*` salvo
  `.env.example` y `.env.supabase.example`.
- No commitear `media/`, `staticfiles/`, `db.sqlite3`, `node_modules/`, `dist/`.
- El Dockerfile no corre migraciones (en producción son un paso explícito); el
  `compose.yaml` de desarrollo sí las corre al levantar.
- La rama por defecto es `main`; los cambios entran por pull request.

## Dónde está la documentación

| Ruta | Contenido |
|---|---|
| `README.md` | Arranque rápido, estructura general, resumen de CI |
| `backend/README.md` | Puesta en marcha, variables del `.env`, errores comunes (incluye `relation "cliente" already exists` y la migración 0008) |
| `Info/Ambientes.md` | Proyectos Supabase de desarrollo y producción |
| `Info/DB.md` | Esquema, estados de un paquete, tamaños y niveles |
| `Info/Docker.md` | Imagen, Docker Hub y tags |
| `Info/CRUD.md` | CRUD de comercios (API + UI) |
| `backend/crudComercios/README.md`, `backend/crudRepartidor/README.md`, `backend/loginCoordinador/README.md` | Contrato JSON, validaciones y tabla de tests de esos tres módulos |
| `Scrums/` | Notas de las dailies del equipo |
