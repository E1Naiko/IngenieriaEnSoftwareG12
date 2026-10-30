"""
Configuración de Django para el proyecto login (Grupo 12).

- Producción: PostgreSQL en Supabase (DATABASE_MODE=postgres).
- Desarrollo: PostgreSQL en un proyecto Supabase separado de producción
  (DATABASE_MODE=postgres); SQLite queda disponible para pruebas offline.
- El frontend React vive en ../frontend y se comunica con esta API por
  HTTP (CORS ya está configurado en este archivo).
"""

from pathlib import Path
import os
import re

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# BASE_DIR = .../backend
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar las credenciales de backend/.env
load_dotenv(BASE_DIR / ".env")


def _env_bool(nombre, por_defecto="True"):
    return os.getenv(nombre, por_defecto).strip().lower() in ("1", "true", "yes", "si", "sí")


# WARNING: mantener la clave secreta en producción fuera del código.
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY") or (
    "django-insecure-solo-para-desarrollo-no-usar-en-produccion"
)

DEBUG = _env_bool("DJANGO_DEBUG", "True")

ALLOWED_HOSTS = [
    h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()
]
if DEBUG and not ALLOWED_HOSTS:
    # En desarrollo aceptamos cualquier host (incluye previews tipo *.e2b.app).
    ALLOWED_HOSTS = ["*"]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceros
    "corsheaders",
    # Proyecto
    "core",
    "crudComercios",
    "crudRepartidor",
    "loginCoordinador",
    "loginRepartidor",
    "ingresarPedido",
    "actualizacionEstado",
    "historialEnvios",
    "pedidosAsignados",
    "consultarEstadoEnvio",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # tiene que ir antes de CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Base de datos
# --------------------------------------------------------------------------


def _resolver_modo_db(environ, debug):
    """Resuelve el backend configurado; los proyectos Supabase usan PostgreSQL."""
    modo = (environ.get("DATABASE_MODE") or "").strip().lower()
    if not modo:
        # En producción no caer silenciosamente en una SQLite efímera si falta
        # la configuración de Supabase. Sin un .env local, DEBUG=True mantiene
        # un fallback SQLite para pruebas offline; .env.example selecciona
        # explícitamente el proyecto Supabase de desarrollo.
        modo = "sqlite" if debug else "postgres"

    if modo not in {"sqlite", "postgres"}:
        raise ImproperlyConfigured(
            "DATABASE_MODE debe ser 'sqlite' (offline/tests) o 'postgres' "
            f"(Supabase); se recibió {modo!r}."
        )
    return modo


def _configurar_db(modo, environ, base_dir):
    if modo == "sqlite":
        ruta_configurada = environ.get("DB_SQLITE_PATH") or base_dir / "db.sqlite3"
        ruta = Path(ruta_configurada).expanduser()
        if not ruta.is_absolute():
            ruta = base_dir / ruta
        return {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ruta,
            }
        }

    # PostgreSQL en Supabase. Se recomienda "Connect → Session pooler".
    # En este modo no hay fallback: un secreto faltante o de plantilla tiene
    # que detener el arranque antes de operar por error sobre otra base.
    valores = {
        "DB_HOST": (environ.get("DB_HOST") or "").strip(),
        "DB_NAME": (environ.get("DB_NAME") or "").strip(),
        "DB_USER": (environ.get("DB_USER") or "").strip(),
        # No se modifica la contraseña: puede contener espacios válidos.
        "DB_PASSWORD": environ.get("DB_PASSWORD") or "",
    }
    incompletos = [
        nombre
        for nombre, valor in valores.items()
        if not valor.strip() or re.search(r"<[^<>]*>", valor)
    ]
    if incompletos:
        raise ImproperlyConfigured(
            "DATABASE_MODE=postgres requiere credenciales de Supabase completas "
            "en backend/.env (o en el entorno del despliegue). Revisá: "
            + ", ".join(incompletos)
            + ". No se usa SQLite como fallback."
        )

    puerto = (environ.get("DB_PORT") or "5432").strip()
    try:
        puerto_numero = int(puerto)
    except ValueError as exc:
        mensaje = "DB_PORT debe ser un número de puerto válido."
        raise ImproperlyConfigured(mensaje) from exc
    if not 1 <= puerto_numero <= 65535:
        raise ImproperlyConfigured("DB_PORT debe estar entre 1 y 65535.")

    return {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": valores["DB_NAME"],
            "USER": valores["DB_USER"],
            "PASSWORD": valores["DB_PASSWORD"],
            "HOST": valores["DB_HOST"],
            "PORT": str(puerto_numero),
            "OPTIONS": {
                "sslmode": (environ.get("DB_SSLMODE") or "require").strip(),
            },
        }
    }


DATABASE_MODE = _resolver_modo_db(os.environ, DEBUG)
DATABASES = _configurar_db(DATABASE_MODE, os.environ, BASE_DIR)


# Validación de contraseñas
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internacionalización
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "es-ar"
TIME_ZONE = "America/Argentina/Buenos_Aires"
USE_I18N = True
USE_TZ = True


# Archivos estáticos y media (comprobantes subidos)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# CORS: qué orígenes (el frontend React) pueden llamar a esta API.
# --------------------------------------------------------------------------
# Se lee del .env (CORS_ALLOWED_ORIGINS, separados por coma). Si está vacío:
#   - entran los puertos clásicos de Vite (localhost y 127.0.0.1), y
#   - con DEBUG=True se acepta cualquier origen, para no bloquear a nadie que
#     prueba desde el tunnel de otro o una IP de la red.
# Con la allowlist vacía y DEBUG=False no se acepta ningún origen cross-site:
# en producción hay que listar el dominio del frontend explícitamente.
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()
]
if not CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
    if DEBUG:
        CORS_ALLOW_ALL_ORIGINS = True

# El frontend llama con rutas relativas (/api/...) proxificadas por Vite, o
# sea mismo origen: la cookie de sesión viaja sin esta opción. Habilitarla
# solo hace falta si algún día el front queda en otro dominio y necesita
# cookies; con CORS_ALLOW_ALL_ORIGINS no se puede combinar (el navegador
# rechaza `Access-Control-Allow-Credentials` junto con `*`).
# CORS_ALLOW_CREDENTIALS = True
