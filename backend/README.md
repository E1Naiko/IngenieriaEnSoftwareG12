# Backend — Django + Supabase para desarrollo y producción

Backend del sistema de reparto de paquetes (app **core**, Grupo 12).

## Que tengo que hacer la primera vez que clono el repositorio?
Seguir [la guía de entornos](../Info/Ambientes.md) y la [documentación de la base](../Info/DB.md).

## Que tengo que hacer para arrancar a programar?

SIEMPRE:
```bash
cd backend
python -m venv venv
source venv/bin/activate        # en Windows: venv\Scripts\activate
                                # en Fish: source venv/bin/activate.fish
pip install -r requirements-dev.txt
```

`requirements-dev.txt` incluye las dependencias de ejecución y las herramientas
de desarrollo; la imagen Docker instala solo `requirements.txt`.

---

## Estructura

```
backend/
├── manage.py            # comandos de Django (runserver, migrate, ...)
├── requirements.txt     # dependencias de ejecución
├── requirements-dev.txt # dependencias para desarrollo y análisis de tipos
├── .env.example         # plantilla del proyecto Supabase de desarrollo
├── .env.supabase.example # plantilla del proyecto Supabase de producción
├── config/              # configuración del proyecto (settings, urls, wsgi)
└── core/                # app principal (modelos, admin, views)
```

## Puesta en marcha

```bash
# 1. Entorno virtual e instalación (desde esta carpeta backend/)
python -m venv venv
source venv/bin/activate          # en Windows: venv\Scripts\activate
pip install -r requirements-dev.txt

# 2. Configuración local con el proyecto Supabase de DESARROLLO
cp .env.example .env
# completar DB_HOST, DB_USER y DB_PASSWORD con las credenciales de desarrollo

# 3. Comprobar el destino, crear las tablas y levantar el servidor
python manage.py revisar_db
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- Admin: http://127.0.0.1:8000/admin/
- Ping para probar desde React: http://127.0.0.1:8000/api/ping/

### Panel "Paquetes en curso" (HU #40)

`GET /api/dashboard/paquetes-en-curso/` devuelve `{"paquetes": [...]}` con los
paquetes que no están `entregado` (la comparación ignora mayúsculas).
`cancelado` es un estado intermediario, así que también se lista. Cada ítem
tiene exactamente cinco claves, que son las que usa
`frontend/src/pages/PaquetesEnCurso.tsx`:

```json
{
  "id": 1,
  "destinatario": "Ana Pérez",
  "direccion": "Calle 12 #34",
  "repartidor": "Juan Gómez",
  "estado": "en_camino"
}
```

`repartidor` vale `"Sin asignar"` si el paquete todavía no tiene uno. Cuando
no hay paquetes activos la respuesta es `200` con `{"mensaje": "...",
"paquetes": []}`. La consulta usa `select_related("repartidor", "cliente")`
para resolver las FKs en un solo query; no incluir `"paquete"` ahí, porque es
el nombre de la relación inversa de `Comprobante`, no un campo de `Paquete`.

Tests del endpoint:

```bash
cd backend
DATABASE_MODE=sqlite python manage.py test paquetesEnCurso
```

`backend/.env.example` selecciona `DATABASE_MODE=postgres` y debe contener
**solo** credenciales del proyecto Supabase de desarrollo. La producción usa
otro proyecto y otras credenciales; no se deben mezclar. Una variable
`DATABASE_MODE` exportada en el entorno sí tiene prioridad sobre `.env`, por
eso conviene verificar el destino con `python manage.py revisar_db` antes de
migrar.

### Verificación de tipos con Pyrefly

Django crea dinámicamente los atributos de los modelos, como `objects`, `id`
y las relaciones inversas `paquetes`. `django-stubs` proporciona a Pyrefly
los tipos de esos atributos y de los campos `CharField`, sin modificar el
comportamiento de la aplicación ni la base de datos.

Con el entorno virtual activado e instaladas las dependencias de desarrollo:

```bash
pip install -r requirements-dev.txt
pyrefly check --preset default core/models.py
```

El comando verifica `core/models.py`, no todo el backend. En el IDE, seleccioná
el mismo intérprete/entorno virtual para Python y Pyrefly. Si el complemento
del editor usa su propia versión de Pyrefly, actualizala a 1.4.0 o posterior;
si los avisos siguen apareciendo, recargá el proyecto o reiniciá el analizador.
No se necesita ejecutar migraciones para corregir estos avisos de tipos.

### Estado `retirado` de los paquetes

`Paquete.Estado.RETIRADO` guarda el valor `retirado` y aparece como **Retirado**
en el admin. El estado inicial sigue siendo `pendiente`; el modelo no cambia
estados automáticamente ni valida el orden de las transiciones. El detalle de
los cinco estados y de la validación de `choices` está en
[Info/DB.md](../Info/DB.md#estados-de-un-paquete).

La migración `core.0006_agregar_estado_retirado_paquete` registra la nueva
opción en Django sin cambiar la columna ni los paquetes existentes. Para
aplicarla en cada base configurada (desarrollo y, durante el despliegue,
producción):

```bash
python manage.py revisar_db        # confirmar la base seleccionada
python manage.py migrate --plan   # incluye cualquier otra migración pendiente
python manage.py migrate
python manage.py showmigrations core  # verificar [X] junto a 0006
```

### Configurar producción con Supabase

La aplicación también usa `DATABASE_MODE=postgres` en producción; la diferencia
es que recibe las credenciales del proyecto Supabase de producción. Para un
despliegue, completar `backend/.env.supabase.example` o cargar sus valores
como secretos/variables del hosting. No copies credenciales reales al repo ni
a la imagen Docker. Si `DJANGO_DEBUG=False` y falta `DATABASE_MODE`, Django
intenta PostgreSQL y falla si faltan credenciales; nunca usa SQLite
silenciosamente.

## Ejecución opcional con Docker

No hace falta Docker para desarrollar: el arranque local anterior se conecta al
proyecto Supabase de desarrollo. Si se quiere contenerizar también el backend,
`compose.yaml` lee `backend/.env` y conecta a **ese mismo proyecto**:

```bash
# Desde la raíz; primero completar backend/.env con credenciales de desarrollo.
docker compose up --build
```

Compose ejecuta `migrate` automáticamente, por eso **no apuntar ese `.env` a
producción**. La SQLite ya no es la base de desarrollo principal. Para los
comandos de administración y el uso de la imagen de Docker Hub, ver
[Info/Docker.md](../Info/Docker.md).

## Errores comunes

### `could not translate host name "aws-0-<region>.pooler.supabase.com"`

Ese error indica que `DB_HOST` no resuelve (suele ser un host de ejemplo o mal
copiado). Si está vacío o contiene `<...>`, la configuración lo detecta antes
de intentar conectar. En desarrollo, revisá que `backend/.env` tenga las
credenciales del proyecto Supabase **de desarrollo**; en producción, usá las
del proyecto de producción. En ambos casos el modo es `DATABASE_MODE=postgres`.
Para trabajar offline se puede cambiar explícitamente a `DATABASE_MODE=sqlite`.
Las credenciales incompletas en modo `postgres` detienen el arranque: Django
no cambia silenciosamente a SQLite.

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
`AddField` de la migración inicial; si falta alguna, vuelve a fallar con el
mismo error).

`revisar_db` informa cuántas filas hay en cada tabla de `core` y en
`auth_user`, para saber si el borrado pierde algo.

**b1) Las tablas de `core` están vacías** → borrá solo esas tablas; `auth`,
`admin`, `django_migrations` y tu usuario de `/admin` quedan intactos. Antes,
verificá con `python manage.py revisar_db` que el host pertenece al proyecto
Supabase de **desarrollo**. Nunca ejecutes estos `DROP` en producción. En
Supabase, *SQL Editor*:

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
> Para recrear la SQLite offline (no Supabase), borrá el archivo y ejecutá la
> migración forzando ese modo: `rm -f db.sqlite3` y luego
> `DATABASE_MODE=sqlite python manage.py migrate`.

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
| `DATABASE_MODE` | `postgres` para Supabase (dev o prod, según credenciales); `sqlite` solo para trabajo offline/tests. Si se omite: `DEBUG=True` → SQLite; `DEBUG=False` → PostgreSQL (sin fallback). |
| `DB_HOST` | Host de Supabase (*Connect → Session pooler*); obligatorio en modo `postgres`. |
| `DB_PORT` | Puerto de PostgreSQL (por defecto `5432`). |
| `DB_NAME` | Nombre de la base (normalmente `postgres`); obligatorio en modo `postgres`. |
| `DB_USER` | Usuario (`postgres.<id-del-proyecto>`); obligatorio en modo `postgres`. |
| `DB_PASSWORD` | Contraseña de Supabase; obligatoria en modo `postgres`. |
| `DB_SSLMODE` | Modo SSL de PostgreSQL; por defecto `require`. |
| `DB_SQLITE_PATH` | Ruta del archivo SQLite cuando `DATABASE_MODE=sqlite`. Por defecto, `backend/db.sqlite3`. |
| `DJANGO_SECRET_KEY` | Clave secreta de Django (definir una propia en producción). |
| `DJANGO_DEBUG` | `True` en desarrollo, `False` en producción. |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos, separados por coma. |
| `CORS_ALLOWED_ORIGINS` | Orígenes del frontend, separados por coma. |

### Representación numérica del tamaño de paquetes (migración 0008)

| Vehículo (`tipo_vehiculo`) | `repartidor.tamanio_maximo_nivel` | Tamaño máximo |
| --- | --- | --- |
| `moto` | 1 | chico |
| `auto` | 2 | mediano |
| `camioneta` | 3 | grande |
| `camion` | 3 | grande |

El número es un **nivel de tamaño**, no una cantidad de paquetes. Se conservan
los strings `repartidor.tipo_vehiculo` y `paquete.tamanio`, junto a sus niveles
numéricos `repartidor.tamanio_maximo_nivel` y `paquete.tamanio_nivel`.

`paquete.tamanio_nivel` vale 1 para `chico`, 2 para `mediano` y 3 para
`grande`. No se agrega un cuarto tamaño. Ambas columnas son enteros
**generados y almacenados por la base**: se completan para las filas existentes
y se recalculan incluso al modificar el vehículo o tamaño con SQL directo.
No se escriben manualmente; después de actualizar una instancia con Django,
usar `refresh_from_db()` para leer su nuevo valor.

La migración convierte `Disponible`/`DISPONIBLE` y variantes con espacios a
`activo`, normaliza los vehículos y tamaños conocidos y conserva otros datos.
Un vehículo/tamaño legado desconocido obtiene nivel `NULL` (requiere revisión;
no debe tratarse como un tamaño de nivel cero). `inactivo` y `baja` no cambian.

Aplicar sobre la base configurada en el entorno correspondiente:

```bash
cd backend
python manage.py migrate
```

Camión se agrega a las opciones del modelo y del formulario de alta. No existe
una tabla independiente de vehículos en este esquema: no se crean repartidores
ficticios ni se cambia el vehículo de los repartidores existentes.
Los contratos JSON conservan los tamaños y vehículos como texto. Para comparar
niveles de tamaño en el ORM, por ejemplo:

```python
# Un paquete puede caber si ambos niveles son conocidos y:
repartidores = Repartidor.objects.filter(
    estado=Repartidor.Estado.ACTIVO,
    tamanio_maximo_nivel__gte=paquete.tamanio_nivel,
) if paquete.tamanio_nivel is not None else Repartidor.objects.none()
```

Esto agrega la representación numérica de los tamaños; no modifica automáticamente la asignación
de pedidos. Las pruebas offline usan SQLite; validar también la migración en
el proyecto PostgreSQL de desarrollo antes de desplegar a producción.

#### Error de collation al aplicar la 0008 en PostgreSQL

La expresión original con `__iexact` generaba `UPPER()` también sobre literales
SQL, lo que podía causar `IndeterminateCollation` al crear las columnas STORED.
La 0008 y los modelos ahora comparan `LOWER(TRIM(columna))` con un literal sin
aplicarle funciones al literal. La collation de la función proviene de la
columna y se conserva la tolerancia a mayúsculas y espacios.

Si el intento falló en PostgreSQL y `showmigrations core` muestra `[ ] 0008`,
actualizar el código y volver a ejecutar `python manage.py migrate`. No marcar
la 0008 con `--fake`: se necesitan sus columnas reales. La migración es atómica,
por lo que el intento fallido se revierte en PostgreSQL.


### Estado ACTIVO en mayúsculas (migración 0009)

El valor persistido y devuelto por la API para repartidores activos es `ACTIVO`.
La migración 0009 actualiza los registros `activo`/`disponible` (incluidas
variantes con mayúsculas y espacios), sin modificar `inactivo` ni `baja`.
El modelo usa `ACTIVO` como valor por defecto. La 0008 no se modifica: para
bases donde ya está aplicada, ejecutar `python manage.py migrate` para aplicar
la corrección de datos y opciones de la 0009.

### Repartidores ficticios para desarrollo

Después de aplicar las migraciones, verificá que el entorno apunte a la base
**de desarrollo** y ejecutá explícitamente:

```bash
python manage.py migrate
python manage.py cargar_repartidores_demo --confirmar-desarrollo
```

Crea 12 repartidores: cada combinación de moto, auto, camioneta y camión con
los estados `ACTIVO`, `inactivo` y `baja`. Así hay un repartidor activo de cada
vehículo para probar la selección por tamaño. Los niveles se calculan en la
base y los tokens se generan automáticamente.

Usa DNIs ficticios 99001000–99001011, correos `@example.invalid` y teléfonos
`0000000000`. Puede repetirse sin duplicar registros ni sobrescribir los
existentes. Si un DNI ya pertenece a otro registro, lo omite con una advertencia.
No reinicia datos demo que se hayan editado. No ejecutar en producción.
