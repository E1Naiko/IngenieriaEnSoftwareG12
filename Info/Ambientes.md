# Bases de datos por entorno

El sistema usa **dos proyectos PostgreSQL independientes en Supabase**:

| Entorno | Base | Configuración que la selecciona |
|---|---|---|
| Desarrollo | Proyecto Supabase de desarrollo, compartido por el equipo | Credenciales de desarrollo en `backend/.env` |
| Producción | Proyecto Supabase de producción | Credenciales de producción cargadas como secretos/variables del hosting |

En los dos casos Django usa `DATABASE_MODE=postgres`. El host, usuario y
contraseña determinan a qué proyecto se conecta. Cada proceso de Django utiliza
una sola base a la vez; no replica ni sincroniza datos entre desarrollo y
producción. Las migraciones crean el mismo esquema en cada proyecto, pero los
registros se mantienen separados.

## Desarrollo

No hace falta Docker para conectarse a la base de desarrollo. Desde la raíz del
repositorio:

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Editar `backend/.env` (o `.env`, si ya estás dentro de `backend/`) y reemplazar
los valores de ejemplo por los del **proyecto Supabase de desarrollo**. Se
obtienen en Supabase → proyecto de desarrollo →
**Connect** → **Session pooler**. Completar, como mínimo:

- `DB_HOST`: host del pooler.
- `DB_PORT`: normalmente `5432`.
- `DB_NAME`: normalmente `postgres`.
- `DB_USER`: usuario del pooler del proyecto de desarrollo.
- `DB_PASSWORD`: contraseña de la base de ese proyecto.

Después, comprobar el destino y crear/actualizar el esquema:

```bash
python manage.py revisar_db
python manage.py migrate
python manage.py runserver
```

`revisar_db` muestra el motor y el host al que se conectará. Confirmar que sea
el **proyecto de desarrollo** antes de ejecutar migraciones o comandos que
escriban datos. No copiar las credenciales de producción al `.env` local.

Si se quiere ejecutar el backend dentro de un contenedor, Compose también lee
`backend/.env` y se conecta al Supabase de desarrollo:

```bash
# Desde la raíz del repo; primero crear backend/.env como se indicó arriba.
docker compose up --build
```

Compose ejecuta `migrate` al iniciar. Por eso no se debe apuntar su `.env` a
producción. Docker es opcional para el backend y **Docker Hub almacena la imagen,
no la base de datos**.

## Producción

La plantilla `backend/.env.supabase.example` contiene las variables esperadas,
pero solo valores ficticios. En el proveedor de hosting, cargarlas como
**secretos/variables de producción** usando las credenciales del proyecto
Supabase de producción. Mantener:

```dotenv
DATABASE_MODE=postgres
DJANGO_DEBUG=False
```

Además de las credenciales (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`,
`DB_PASSWORD`), configurar una `DJANGO_SECRET_KEY` propia y los dominios reales
en `DJANGO_ALLOWED_HOSTS` y `CORS_ALLOWED_ORIGINS`. No subir un `.env` con
credenciales reales a Git ni incorporarlo a la imagen.

Aplicar `python manage.py migrate --noinput` como paso controlado del
despliegue, después de verificar que las variables pertenecen al proyecto de
producción. Si `DATABASE_MODE=postgres` y faltan credenciales o siguen teniendo
marcadores como `<region>`, Django detiene el arranque: no cambia
silenciosamente a SQLite.

## Tests y alternativa offline

Para que los tests no creen una base temporal en Supabase, ejecutarlos con
SQLite local:

```bash
cd backend
DATABASE_MODE=sqlite python manage.py test
```

SQLite también está disponible para trabajar sin conexión. En ese modo,
`DB_SQLITE_PATH` puede elegir el archivo local; de forma predeterminada es
`backend/db.sqlite3`.
El archivo no se sube a Git ni a Docker Hub.

## Reglas de seguridad

1. Usar credenciales distintas para desarrollo y producción.
2. Verificar el destino con `python manage.py revisar_db` antes de migrar.
3. No ejecutar comandos destructivos ni pruebas que escriban datos contra
   producción.
4. No compartir contraseñas ni secretos por el repositorio o por chat.
5. No confundir la imagen de Docker Hub con una base persistente: los datos
   permanecen en el servicio Supabase correspondiente.
