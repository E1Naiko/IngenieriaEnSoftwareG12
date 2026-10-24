# Ingeniería en Software — Grupo 12

Sistema de gestión de reparto de paquetes (app **core**): backend en **Django**
con base **PostgreSQL en Supabase** y frontend en **React**. Para desarrollo,
el backend puede usar **SQLite** sin credenciales externas.

## Estructura

```text
frontend/       → app React
backend/        → API Django + Supabase/SQLite (ver backend/README.md)
Info/           → documentación del dominio y del esquema de datos
compose.yaml    → backend de desarrollo con SQLite persistente
.github/        → tests y build en todas las ramas; publicación en Docker Hub
```

## Arranque rápido con Docker

Con Docker y Docker Compose instalados, desde la raíz:

```bash
docker compose up --build
```

Esto crea o actualiza la base SQLite de desarrollo, aplica las migraciones y
levanta la API en http://localhost:8000. La base se conserva en un volumen al
detener o reconstruir el contenedor; no se sube a Git ni a Docker Hub.

Para el frontend, en otra terminal:

```bash
cd frontend
npm install
npm run dev
```

Ver [Info/Docker.md](Info/Docker.md) para los comandos de administración, el
borrado de la base de desarrollo y la configuración de Docker Hub.

## Arranque local sin Docker

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Dejar DB_HOST vacío para SQLite o completar las credenciales de Supabase.
python manage.py migrate
python manage.py runserver
```

En Windows, la activación del entorno es `venv\Scripts\activate`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Instrucciones completas en [backend/README.md](backend/README.md).
Documentación de modelos y decisiones de diseño en [Info/DB.md](Info/DB.md).

## CI y publicación en Docker Hub

El workflow de GitHub Actions corre **tests y build en cualquier rama** y en
todos los pull requests. La build además se prueba levantando el contenedor y
consultando `/api/ping/`.

La publicación es automática solo en `main` (`latest` y `main-<sha>`). En ramas
de desarrollo es **opcional**: se pide con `[publicar-imagen]` en el mensaje
del commit, con la variable `DOCKERHUB_PUBLISH_DEV=true` o ejecutando el
workflow a mano; en ese caso publica únicamente `dev-<rama>-<sha>` y nunca
toca `latest`. Los pull requests jamás publican.

Hay que configurar una sola vez los secretos `DOCKERHUB_USERNAME` y
`DOCKERHUB_TOKEN` en GitHub Actions. El detalle de los tags, las formas de
publicar y cómo verificar esas credenciales está en
[Info/Docker.md](Info/Docker.md#ci-tests-y-build-en-cualquier-rama).

> Nota: el PR #26 se integró en `DjangoImport`; hasta que el workflow llegue a
> `main` no se publica `latest` ni aparece el botón *Run workflow* en Actions.
