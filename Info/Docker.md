# Docker, SQLite de desarrollo y Docker Hub

La imagen publicada contiene **el backend Django**. El frontend React se sigue
ejecutando con Vite y consume la API expuesta en el puerto `8000`.

## Desarrollo con SQLite

Requisitos: Docker con el plugin Docker Compose. No hace falta crear
`backend/.env` ni tener credenciales de Supabase.

Desde la raíz del repositorio:

```bash
docker compose up --build
```

El servicio hace lo siguiente:

1. Construye la imagen desde `backend/Dockerfile`.
2. Fuerza `DB_HOST=` para activar el fallback a SQLite ya existente.
3. Guarda la base en `/data/db.sqlite3`, dentro del volumen `sqlite_data`.
4. Ejecuta `python manage.py migrate --noinput` antes de iniciar Django.
5. Expone la API en http://localhost:8000 y el admin en
   http://localhost:8000/admin/.

Para probar que responde:

```bash
curl http://localhost:8000/api/ping/
```

La base y los archivos subidos **no quedan dentro de la imagen**. Sobreviven a
`docker compose down`, a `docker compose up --build` y a la recreación del
contenedor gracias a los volúmenes `sqlite_data` y `media_data`.

### Comandos habituales

Con el contenedor levantado:

```bash
# Crear un usuario para /admin/
docker compose exec backend python manage.py createsuperuser

# Revisar el esquema y las migraciones
docker compose exec backend python manage.py revisar_db

# Ejecutar la suite de tests
docker compose exec backend python manage.py test

# Ver los logs
docker compose logs -f backend
```

Para detener los servicios sin borrar los datos:

```bash
docker compose down
```

Para **recrear desde cero la base y los archivos subidos de desarrollo**:

```bash
# Atención: -v elimina los volúmenes sqlite_data y media_data de este proyecto.
docker compose down -v
docker compose up --build
```

Esto no borra un `backend/db.sqlite3` que se haya creado al ejecutar Django
fuera de Docker; son dos bases independientes.

### Cambios en el código

El Compose no monta el código fuente dentro del contenedor: después de un
cambio hay que reconstruir la imagen:

```bash
docker compose up --build
```

Las migraciones se vuelven a aplicar solas. Los datos del volumen se conservan.
Si se prefiere trabajar con recarga inmediata sin reconstruir, se puede seguir
usando el arranque local descripto en `backend/README.md`.

## SQLite fuera de Docker

El comportamiento anterior no cambia: con `DB_HOST` vacío se usa
`backend/db.sqlite3`.

```bash
cd backend
python manage.py migrate
python manage.py runserver
```

Opcionalmente, `DB_SQLITE_PATH` permite elegir otro archivo. Las rutas
relativas se resuelven desde `backend/`:

```dotenv
DB_HOST=
DB_SQLITE_PATH=data/desarrollo.sqlite3
```

Hay que crear el directorio destino si no existe. El archivo SQLite y los datos
no se versionan; cualquier desarrollador puede recrear el esquema con las
migraciones.

## Publicación automática desde `main`

El workflow `.github/workflows/docker-hub.yml`:

- ejecuta los tests con SQLite en los pull requests dirigidos a `main`;
- al hacer push o merge en `main`, vuelve a ejecutar los tests;
- solo si los tests pasan, construye y publica el backend en Docker Hub;
- publica los tags `latest` y `main-<sha-del-commit>`.

### Configuración única

1. Crear en Docker Hub el repositorio
   `<usuario>/ingenieria-en-software-g12-backend`.
2. Crear un **access token de Docker Hub con permiso de escritura**. No usar ni
   guardar la contraseña de la cuenta en GitHub Actions.
3. En GitHub, abrir **Settings → Secrets and variables → Actions** del
   repositorio y crear estos **repository secrets**:

   | Nombre | Valor |
   |---|---|
   | `DOCKERHUB_USERNAME` | Usuario de Docker Hub. |
   | `DOCKERHUB_TOKEN` | Access token de Docker Hub. |

   Los valores se cargan en GitHub; no deben enviarse por chat ni agregarse al
   código.

4. Opcional: si el repositorio de Docker Hub tiene otro nombre, crear la
   **repository variable** `DOCKERHUB_REPOSITORY` con ese nombre (sin incluir
   el usuario). Por defecto se usa `ingenieria-en-software-g12-backend`.

Después, al integrar cambios en `main`, la publicación aparece en la pestaña
**Actions → Tests y Docker Hub**. También se puede ejecutar manualmente desde
esa pestaña usando **Run workflow** sobre `main`.

La imagen resultante se puede descargar con:

```bash
docker pull <usuario>/ingenieria-en-software-g12-backend:latest
```

## Uso de la imagen publicada

En producción hay que proporcionar una configuración real mediante variables
de entorno: como mínimo `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`,
`DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` y las credenciales PostgreSQL.
El fallback a SQLite está pensado para desarrollo, no como almacenamiento de
producción.

Las migraciones son un paso explícito y no se ejecutan en cada arranque de la
imagen de producción. Por ejemplo, usando un `.env` ya configurado que no está
incluido en la imagen:

```bash
# Aplicar migraciones una vez por despliegue.
docker run --rm \
  --env-file backend/.env \
  <usuario>/ingenieria-en-software-g12-backend:latest \
  python manage.py migrate --noinput

# Levantar el servidor WSGI.
docker run -d \
  --name srfr-backend \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file backend/.env \
  <usuario>/ingenieria-en-software-g12-backend:latest
```

`backend/.dockerignore` excluye `.env`, los SQLite locales, `media/` y demás
artefactos para que ninguna credencial o base de desarrollo termine publicada
en Docker Hub.
