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
.github/        → tests y publicación de la imagen desde main
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

## Publicación en Docker Hub

Los pull requests a `main` ejecutan los tests del backend. Cada push o merge a
`main` vuelve a probar el código y, si está verde, publica
`<usuario>/ingenieria-en-software-g12-backend:latest` y un tag identificado por
el SHA del commit.

Hay que configurar una sola vez los secretos `DOCKERHUB_USERNAME` y
`DOCKERHUB_TOKEN` en GitHub Actions. El paso a paso está en
[Info/Docker.md](Info/Docker.md#publicación-automática-desde-main).
