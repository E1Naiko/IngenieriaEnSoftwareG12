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

### `ModuleNotFoundError: No module named 'django'`

El entorno virtual no está activado (o `pip install` se corrió en otro
Python). Verificar con `which python`: tiene que apuntar a `backend/venv/bin/python`.

## CORS (frontend React)

El frontend puede llamar a la API sin tocar nada si corre en
`http://localhost:5173` (Vite) o `http://localhost:3000` (CRA), ya que con
`DEBUG=True` se acepta cualquier origen. Para restringirlo, completar
`CORS_ALLOWED_ORIGINS` en el `.env`.

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
