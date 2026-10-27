# Docker, Supabase y Docker Hub

La imagen publicada contiene **el backend Django**. El frontend React se sigue
ejecutando con Vite y consume la API expuesta en el puerto `8000`.

La base de desarrollo y la de producción son **dos proyectos Supabase
separados**. En local se usa `backend/.env` con las credenciales del proyecto
de desarrollo; el hosting de producción recibe las credenciales de producción
como secretos. No se mezclan ni se suben a Git.

> Docker Hub almacena imágenes, no bases de datos vivas. Para desarrollar no
> hace falta Docker: Django se puede ejecutar localmente y conectarse al
> Supabase de desarrollo. Docker es opcional para contenerizar el backend; la
> base sigue estando en Supabase.

## Desarrollo local sin Docker

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# completar DB_HOST, DB_USER y DB_PASSWORD del proyecto Supabase de desarrollo
python manage.py revisar_db    # comprobar que apunta al proyecto de desarrollo
python manage.py migrate
python manage.py runserver
```

La API queda en http://localhost:8000. Antes de migrar, verificar siempre el
resultado de `revisar_db`; la plantilla de desarrollo no debe contener el host
ni la contraseña de producción.

## Ejecución opcional con Docker Compose

Compose también usa las variables de `backend/.env` y conecta al Supabase de
desarrollo (no guarda una SQLite). Desde la raíz del repositorio:

```bash
cp backend/.env.example backend/.env
# completar las credenciales del proyecto de desarrollo
docker compose up --build
```

El contenedor ejecuta `migrate` al arrancar y expone la API en el puerto `8000`.
**No apuntar `backend/.env` a producción:** Compose migra la base configurada.
Los archivos subidos quedan en el volumen `media_data`; `docker compose down -v`
borra esos archivos locales, pero no borra la base remota de Supabase.

Comandos habituales:

```bash
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py revisar_db
# Las pruebas usan SQLite aislada y no crean una base de test en Supabase.
docker compose exec backend env DATABASE_MODE=sqlite python manage.py test
docker compose logs -f backend
```

Después de cambiar código hay que reconstruir la imagen con
`docker compose up --build`. Para trabajar con recarga inmediata, ejecutar el
backend localmente sin Docker.

## SQLite opcional para trabajo offline

SQLite queda disponible para pruebas locales sin conexión a Supabase; no es la
base compartida de desarrollo. Desde `backend/`:

```bash
DATABASE_MODE=sqlite python manage.py migrate
DATABASE_MODE=sqlite python manage.py runserver
```

Por defecto el archivo es `backend/db.sqlite3`. `DB_SQLITE_PATH` permite
seleccionar otra ruta; las rutas relativas se resuelven desde `backend/` y el
directorio debe existir. El archivo se ignora en Git.

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

4. Opcional: crear **repository variables** (pestaña *Variables*, no
   *Secrets*, porque no son datos sensibles):

   | Nombre | Valor por defecto | Para qué sirve |
   |---|---|---|
   | `DOCKERHUB_REPOSITORY` | `ingenieria-en-software-g12-backend` | Nombre del repositorio en Docker Hub, sin el usuario. Solo minúsculas, números, `.`, `_` o `-`. |
   | `DOCKERHUB_PUBLISH_DEV` | `false` | `true` publica un tag `dev-...` en cada push de ramas que no sean `main`. |

   Si ya se crearon en la pestaña **Secrets** (por ejemplo
   `DOCKERHUB_REPOSITORY` junto a los otros dos), el workflow **también los
   lee**: primero busca la *variable* y, si no existe, cae al *secret* del
   mismo nombre. El resumen de cada corrida indica de dónde salió cada valor.
   Igual conviene moverlos a *Variables*: mientras sean secrets, GitHub
   enmascara su valor en los logs y en el resumen, lo que dificulta revisar la
   configuración.

### Verificar `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN`

**En la UI de GitHub.** **Settings → Secrets and variables → Actions →
Repository secrets** deben listar `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN`
(con su fecha de última actualización). GitHub nunca muestra los valores: si
hay dudas, hay que regenerar el access token en Docker Hub y volver a cargarlo
(Update). Los secretos de entorno/organización no aplican acá: se usan
*repository secrets*. Ojo con la pestaña: si `DOCKERHUB_REPOSITORY` o
`DOCKERHUB_PUBLISH_DEV` aparecen bajo **Secrets** en vez de **Variables**, el
workflow igual los toma (ver el fallback en el paso 4), pero lo correcto es
tenerlos como variables.

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
de entorno: `DATABASE_MODE=postgres`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`,
`DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` y las credenciales PostgreSQL.
La plantilla es `backend/.env.supabase.example`; completar los valores reales
antes de usarla. Si `DJANGO_DEBUG=False` y no se define `DATABASE_MODE`, Django
elige PostgreSQL, y si faltan credenciales detiene el arranque: nunca cambia a
SQLite silenciosamente.

Las migraciones son un paso explícito y no se ejecutan en cada arranque de la
imagen de producción. No reutilices el `backend/.env` local (de desarrollo).
Para usar Docker manualmente, crea un archivo ignorado con los secretos de
producción a partir de la plantilla; en el hosting, inyecta esos valores como
secretos del servicio:

```bash
# Preparación local opcional (archivo ignorado por Git):
cp backend/.env.supabase.example backend/.env.production
# Completarlo con las credenciales del proyecto Supabase de producción.

# Aplicar migraciones una vez por despliegue.
docker run --rm \
  --env-file backend/.env.production \
  <usuario>/ingenieria-en-software-g12-backend:latest \
  python manage.py migrate --noinput

# Levantar el servidor WSGI.
docker run -d \
  --name srfr-backend \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file backend/.env.production \
  <usuario>/ingenieria-en-software-g12-backend:latest
```

`backend/.dockerignore` excluye `.env`, los SQLite locales, `media/` y demás
artefactos para que ninguna credencial o base de desarrollo termine publicada
en Docker Hub.
