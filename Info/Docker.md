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

## CI: tests y build en cualquier rama

El workflow `.github/workflows/docker-hub.yml` se dispara en:

- `push` a **cualquier** rama (`branches: ["**"]`);
- `pull_request` hacia cualquier rama;
- `workflow_dispatch` (ejecución manual con opciones, ver más abajo).

Tiene estos jobs:

| Job | Cuándo corre | Qué hace |
|---|---|---|
| `Calcular tags y decidir publicación` | siempre | Normaliza la rama, calcula el SHA corto, arma los tags y decide si se publica. Escribe la decisión en el resumen de la corrida. |
| `Tests del backend con SQLite` | siempre | Python 3.12, `manage.py check`, `makemigrations --check --dry-run` y `manage.py test`. |
| `Construir y probar la imagen (sin publicar)` | siempre, después de los tests | Build con Buildx, `manage.py check` dentro de la imagen y un `GET /api/ping/` real al contenedor. **No usa secretos**: por eso también funciona en PR de forks. |
| `Publicar imagen en Docker Hub` | solo si se pidió publicación | Verifica los secretos, hace login y empuja la imagen. |
| `Verificar credenciales de Docker Hub (sin publicar)` | casilla `check_credentials` en Run workflow **o** marca `[verificar-dockerhub]` en el commit | Comprueba que existan los secretos y valida el token con `docker login`. No publica nada. |

### Regla de tags

| Situación | Tags generados | ¿Publica? |
|---|---|---|
| Push o merge en `main` | `latest`, `main-<sha7>` | Sí, siempre |
| Push en otra rama | `dev-<rama>-<sha7>` | Solo si se pide (ver abajo) |
| Pull request | `dev-<rama>-<sha7>` (solo locales, para el build) | **Nunca** |
| Ejecución manual | los que correspondan a la rama elegida | Solo si se marca `publish` |

`latest` queda **reservado para `main`**; ninguna rama de desarrollo lo toca. El tag
de desarrollo se normaliza para cumplir las reglas de Docker: minúsculas, `/` y
cualquier carácter inválido reemplazados por `-`, y la rama se trunca a 80
caracteres para no superar el límite de 128 del tag. Ejemplo:

```text
rama  arena/mi-rama        →  dev-arena-mi-rama-a1b2c3d
rama  DjangoImport         →  dev-djangoimport-a1b2c3d
main                       →  latest  +  main-a1b2c3d
```

Los pull requests nunca publican, aunque el mensaje del commit incluya la marca
de publicación: el código de un PR (sobre todo de un fork) no se ejecuta con
credenciales de Docker Hub.

### Cómo pedir una publicación desde una rama de desarrollo

Tres vías, de más puntual a más automática:

1. **Marca en el commit** (recomendada para una imagen suelta). Incluir
   `[publicar-imagen]` (también se acepta `[publish-image]`) en el mensaje:

   ```bash
   git commit -m "feat: ajustes de API [publicar-imagen]"
   git push origin mi-rama
   ```

   Se publica `<usuario>/ingenieria-en-software-g12-backend:dev-mi-rama-<sha7>`.

2. **Variable de repositorio `DOCKERHUB_PUBLISH_DEV=true`**. En
   **Settings → Secrets and variables → Actions → Variables**, crear esa
   *repository variable* para que **todo** push en ramas que no sean `main`
   publique su tag `dev-...`. Borrarla o ponerla en `false` vuelve al
   comportamiento por defecto (solo build). Es la opción práctica mientras el
   workflow no está en la rama por defecto y el botón *Run workflow* no existe.

3. **Ejecución manual**. En **Actions → Tests, build y Docker Hub → Run
   workflow**, elegir la rama y marcar `publish`. Con `publish` desmarcado la
   corrida hace solo tests y build, incluso en `main`.

> **Limitación de GitHub:** el botón *Run workflow* y el evento
> `workflow_dispatch` solo están disponibles cuando el archivo del workflow
> existe en la **rama por defecto**. Los eventos `push`, en cambio, usan el
> workflow de la rama que se empuja, así que las vías 1 y 2 funcionan en ramas
> de desarrollo aunque `main` todavía no tenga el YAML. Lo mismo aplica a
> `check_credentials`: hasta que el workflow llegue a `main`, la verificación
> del token se hace con la marca `[verificar-dockerhub]` en el mensaje de un
> commit (ver más abajo) o localmente con `docker login -u <usuario>` y el
> access token.

> **Estado al hacer este cambio (2026-10-24):** el PR #26 se integró en
> `DjangoImport`, pero `main` todavía no tenía
> `.github/workflows/docker-hub.yml` (la API de GitHub devolvía 0 workflows y
> 0 corridas). Hasta que el archivo llegue a `main` no se publica `latest` ni
> aparece el botón *Run workflow*. Mientras tanto, los push en `DjangoImport` y
> en las ramas de trabajo sí ejecutan tests y build, porque los eventos `push`
> leen el workflow de la rama que se empuja.

### Configuración única

1. Crear en Docker Hub el repositorio
   `<usuario>/ingenieria-en-software-g12-backend`.
2. Crear un **access token de Docker Hub con permiso de escritura**
   (*Read, Write*). No usar ni guardar la contraseña de la cuenta en GitHub
   Actions.
3. En GitHub, abrir **Settings → Secrets and variables → Actions** del
   repositorio y crear estos **repository secrets**:

   | Nombre | Valor |
   |---|---|
   | `DOCKERHUB_USERNAME` | Usuario de Docker Hub. |
   | `DOCKERHUB_TOKEN` | Access token de Docker Hub con permiso de escritura. |

   Los valores se cargan en GitHub; no deben enviarse por chat ni agregarse al
   código.

4. Opcional: crear **repository variables** (pestaña *Variables*):

   | Nombre | Valor por defecto | Para qué sirve |
   |---|---|---|
   | `DOCKERHUB_REPOSITORY` | `ingenieria-en-software-g12-backend` | Nombre del repositorio en Docker Hub, sin el usuario. Solo minúsculas, números, `.`, `_` o `-`. |
   | `DOCKERHUB_PUBLISH_DEV` | `false` | `true` publica un tag `dev-...` en cada push de ramas que no sean `main`. |

### Verificar `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN`

**En la UI de GitHub.** **Settings → Secrets and variables → Actions →
Repository secrets** deben listar ambos nombres (con su fecha de última
actualización). GitHub nunca muestra los valores: si hay dudas, hay que
regenerar el access token en Docker Hub y volver a cargarlo (Update). Los
secretos de entorno/organización no aplican acá: se usan *repository secrets*.

**Por CLI** (requiere un token con el permiso `secrets:read`; el de integración
de este entorno recibe `403 Resource not accessible by integration`, así que no
se pudo comprobar desde acá):

```bash
gh secret list --repo E1Naiko/IngenieriaEnSoftwareG12
```

Solo lista nombres y fechas, nunca valores.

**En CI.** El job `Verificar credenciales de Docker Hub (sin publicar)` se
puede lanzar de dos maneras:

- **Run workflow → `check_credentials` marcado** (cuando el YAML ya está en
  `main`).
- **Marca en el commit** (funciona en cualquier rama, sin botón de Actions):

  ```bash
  git commit --allow-empty -m "chore: revisar credenciales [verificar-dockerhub]"
  git push origin mi-rama
  ```

  El commit vacío no cambia el código y no publica ninguna imagen.

Comprueba la presencia de ambos secretos y hace un `docker login` real (con
*logout* al final): si el token está mal, fue revocado o el usuario no coincide,
la corrida falla. Ningún valor se imprime en los logs. Si falta alguno de los
dos, el mensaje `::error::` indica cuál.

Toda publicación ejecuta además un **chequeo previo** que falla con un mensaje
explícito si falta `DOCKERHUB_USERNAME` o `DOCKERHUB_TOKEN`. Un token válido
pero sin permiso de escritura pasa el login y falla recién en el push con
`denied: requested access to the resource is denied`; en ese caso hay que crear
un access token con permiso *Read, Write* en Docker Hub Security → Access
Tokens.

**Permiso de escritura.** El `docker login` solo prueba que el usuario y el
token son correctos, no que el token pueda subir imágenes. Para comprobarlo sin
esperar a que el workflow llegue a `main`, alcanza con pedir una publicación de
prueba desde una rama de desarrollo:

```bash
git commit --allow-empty -m "chore: probar permiso de escritura [publicar-imagen]"
git push origin mi-rama
```

Si el job `Publicar imagen en Docker Hub` termina bien, el token tiene permiso
de escritura y el repositorio existe. Si falla con `denied: ...`, hay que
revisar el scope del token (y que el repositorio
`<usuario>/ingenieria-en-software-g12-backend` esté creado).

Para ver el resultado: **Actions → Tests, build y Docker Hub →** la corrida
correspondiente → resumen (*Summary*) y logs del job.

La imagen `latest` se descarga con:

```bash
docker pull <usuario>/ingenieria-en-software-g12-backend:latest
```

Y una imagen de desarrollo, con el tag que muestra el resumen de la corrida:

```bash
docker pull <usuario>/ingenieria-en-software-g12-backend:dev-mi-rama-a1b2c3d
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
