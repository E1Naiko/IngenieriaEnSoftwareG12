# Backend — Django + PostgreSQL (Supabase)

Backend del sistema de reparto de paquetes (app **core**, Grupo 12).

## Que tengo que hacer la primera vez que clono el repositorio?
Seguir guia en [DB.md](Info/DB.md).

## Que tengo que hacer para arrancar a programar?

SIEMPRE:
```bash
cd backend
python -m venv venv
source venv/bin/activate        # en Windows: venv\Scripts\activate
                                # en Fish: source venv/bin/activate.fish
pip install -r requirements.txt
```

---

## Estructura

```
backend/
├── manage.py            # comandos de Django (runserver, migrate, ...)
├── requirements.txt     # dependencias
├── .env.example         # plantilla de credenciales → copiar como .env
├── config/              # configuración del proyecto (settings, urls, wsgi)
└── core/                # app principal (modelos, admin, views)
```

## Puesta en marcha

```bash
# 1. Entorno virtual e instalación (desde esta carpeta backend/)
python -m venv venv
source venv/bin/activate          # en Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Credenciales
cp .env.example .env
# editar .env con los datos de Supabase (los pasa quien creó el proyecto)

# 3. Base de datos y servidor
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- Admin: http://127.0.0.1:8000/admin/
- Ping para probar desde React: http://127.0.0.1:8000/api/ping/

> Sin `.env` (o con `DB_HOST` vacío) Django usa una **SQLite local**, así
> nadie queda bloqueado para desarrollar.

## Errores comunes

### `could not translate host name "aws-0-<region>.pooler.supabase.com"`

El `.env` es la plantilla sin completar: los valores con `<...>` son de
ejemplo, no credenciales reales. Dos opciones:

- **No tenés las credenciales todavía**: dejá `DB_HOST` vacío (`DB_HOST=`) y
  Django usa la SQLite local.
- **Sí las tenés**: reemplazá `DB_HOST`, `DB_USER` y `DB_PASSWORD` por los de
  Supabase (*Connect → Session pooler*).

Django detecta los valores con `<...>` y avisa por consola antes de caer a
SQLite, para que el error de arriba no vuelva a aparecer.

### `Your models in app(s): 'core' have changes that are not yet reflected in a migration`

`models.py` cambió (campos o `choices`) pero no se generó la migración. Es un
aviso de `migrate`, no un error: la base sigue funcionando, pero esos cambios
no se aplican.

```bash
python manage.py makemigrations core
python manage.py migrate
```

`revisar_db` también lo detecta y lista las operaciones pendientes:

```
Cambios en los modelos sin migración:
  - Alter field tipo_vehiculo on repartidor
```

> Si tocaste `choices` y el aviso no desaparece, revisá que el cambio esté
> commiteado en `models.py`: el estado de las migraciones se compara contra el
> archivo, no contra la base.

### `ModuleNotFoundError: No module named 'django'`

El entorno virtual no está activado (o `pip install` se corrió en otro
Python). Verificar con `which python`: tiene que apuntar a `backend/venv/bin/python`.

### `django.db.utils.ProgrammingError: relation "cliente" already exists`

La base (Supabase o tu `db.sqlite3` local) **ya tiene tablas del esquema
anterior** y las migraciones actuales intentan crearlas de nuevo: se
regeneraron y `django_migrations` no tiene el registro de `core.0001_initial`.

Primero, para ver el estado exacto (no modifica nada):

```bash
python manage.py revisar_db
```

El comando compara las tablas que existen con las que esperan los modelos y
dice cuál de los dos casos es:

**a) Las tablas coinciden con los modelos** → solo falta registrar la
migración, sin borrar datos:

```bash
python manage.py migrate --fake-initial
```

**b) Las tablas viejas no coinciden** → hay que borrar esas tablas y
recrearlas. Ojo: `--fake-initial` **tampoco sirve acá** (Django solo da la
migración por aplicada si las tablas existen *y* tienen las columnas de los
`AddField`, como `cliente.comercio_id`; si falta alguna, vuelve a fallar con
el mismo error).

`revisar_db` informa cuántas filas hay en cada tabla de `core` y en
`auth_user`, para saber si el borrado pierde algo.

**b1) Las tablas de `core` están vacías** (lo habitual en desarrollo) → borrá
solo esas tablas; `auth`, `admin`, `django_migrations` y tu usuario de
`/admin` quedan intactos. En Supabase, *SQL Editor*:

```sql
drop table if exists paquete, comprobante, cliente, comercio, repartidor cascade;
```

y después:

```bash
python manage.py migrate
python manage.py revisar_db      # debería decir "Todo en orden"
```

**b2) Hay datos que no querés perder / querés empezar de cero** → recreá todo
el schema. ⚠️ Esto borra **todos** los datos, incluidos los usuarios:

```sql
drop schema public cascade;
create schema public;
grant all on schema public to postgres;
grant usage on schema public to anon, authenticated, service_role;
alter default privileges in schema public grant all on tables to postgres, anon, authenticated, service_role;
alter default privileges in schema public grant all on functions to postgres, anon, authenticated, service_role;
alter default privileges in schema public grant all on sequences to postgres, anon, authenticated, service_role;
```

y después:

```bash
python manage.py migrate
python manage.py createsuperuser   # el usuario de /admin se borró
```

> ⚠️ Esto **borra los datos** de esa base. Si hay algo que quieras conservar,
> avisá antes de dropear y se migra tabla por tabla (`rename` + copia).
>
> Para una SQLite local alcanza con borrar el archivo:
> `rm db.sqlite3 && python manage.py migrate`.

### `database "test_postgres" already exists` / `ObjectInUse: database "test_postgres" is being accessed by other users`

Ocurría al correr `python manage.py test` apuntando al *Session pooler* de
Supabase (`*.pooler.supabase.com`), que redirige las conexiones a la base
compartida `postgres` y retiene sesiones abiertas impidiendo el `DROP DATABASE`
al finalizar.

`settings.py` ya fuerza **SQLite en memoria** automáticamente durante
`python manage.py test`, sin importar qué credenciales haya en `.env`. Si en
Supabase quedó una base `test_postgres` huérfana de corridas anteriores, es
inofensiva (o se puede borrar desde *SQL Editor* con
`drop database if exists test_postgres;`).

## CORS (frontend React)

Con `DEBUG=True` y `CORS_ALLOWED_ORIGINS` vacío en el `.env`, Django acepta
cualquier origen: alcanza para llamar la API desde Vite, desde la IP de la
red de un compañero o desde un túnel, sin configurar nada.

Si el front usa rutas relativas (`/api/...`, como hace este proyecto), las
llamadas las proxifica Vite (`server.proxy` en `vite.config.ts`) y son
**mismo origen**: ni siquiera interviene CORS. La allowlist solo importa
cuando alguien llama a `http://127.0.0.1:8000/...` directamente.

Para producción (`DEBUG=False`): listar en el `.env` el dominio del frontend,
separado por coma:

```
CORS_ALLOWED_ORIGINS=https://mi-front.vercel.app,https://www.mi-front.com
```

Con `DEBUG=False` y la variable vacía no se permite ningún origen cross-site.

## Variables del `.env`

| Variable | Descripción |
|---|---|
| `DB_HOST` | Host de Supabase (sección *Session pooler*). Vacío → SQLite local. |
| `DB_PORT` | Puerto (5432). |
| `DB_NAME` | Nombre de la base (postgres). |
| `DB_USER` | Usuario (`postgres.<id-del-proyecto>`). |
| `DB_PASSWORD` | Contraseña de la base. |
| `DJANGO_SECRET_KEY` | Clave secreta (en dev hay una por defecto). |
| `DJANGO_DEBUG` | `True` en desarrollo, `False` en producción. |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos, separados por coma. |
| `CORS_ALLOWED_ORIGINS` | Orígenes del frontend, separados por coma. |
