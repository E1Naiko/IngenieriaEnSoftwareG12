# Ingeniería en Software — Grupo 12

Sistema de gestión de reparto de paquetes (app **core**) hecho con **Django**
y **React**. Usa dos proyectos PostgreSQL en Supabase: uno para desarrollo y
otro para producción. SQLite queda como alternativa local offline.

## Estructura

```text
frontend/       → app React
backend/        → API Django + Supabase (proyectos separados por entorno)
Info/           → documentación del dominio, bases y Docker
compose.yaml    → opción para ejecutar el backend en contenedor
.github/        → tests y build en todas las ramas; publicación en Docker Hub
```

## Arranque rápido de desarrollo (sin Docker)

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# completar DB_HOST, DB_USER y DB_PASSWORD del proyecto Supabase de desarrollo
python manage.py revisar_db  # verificar el destino
python manage.py migrate
python manage.py runserver
```

El backend usa el proyecto Supabase de desarrollo; producción tiene otras
credenciales y otro proyecto. Para el frontend, en otra terminal:

```bash
cd frontend
npm install
npm run dev
```

Docker Compose es opcional para ejecutar el backend en contenedor y también
conecta a Supabase de desarrollo. Ver [Info/Docker.md](Info/Docker.md) para
esa opción y la publicación de imágenes en Docker Hub.

## Producción y pruebas

En el hosting, configurar `DATABASE_MODE=postgres`, `DJANGO_DEBUG=False` y las
credenciales del proyecto Supabase de **producción** usando
`backend/.env.supabase.example` como plantilla. No reutilizar los valores de
desarrollo ni subir credenciales a Git.

Para ejecutar tests localmente sin crear una base de test remota, usar:

```bash
cd backend
DATABASE_MODE=sqlite python manage.py test
```

Instrucciones completas en [backend/README.md](backend/README.md).
Configuración de desarrollo/producción en [Info/Ambientes.md](Info/Ambientes.md);
documentación del esquema en [Info/DB.md](Info/DB.md).

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
