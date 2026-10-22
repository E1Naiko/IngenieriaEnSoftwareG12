"""
Configuración de Django para el proyecto login (Grupo 12).

- La base de datos PostgreSQL está en Supabase: las credenciales se leen
  del archivo .env (ver .env.example). Si DB_HOST está vacío se usa una
  SQLite local para poder desarrollar sin conexión.
- El frontend React vive en ../frontend y se comunica con esta API por
  HTTP (CORS ya está configurado en este archivo).
"""

from pathlib import Path
import os
import re
import warnings

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
    "loginCoordinador",
    "repartidoresDisponibles",
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

DB_HOST = os.getenv("DB_HOST", "").strip()


def _sin_completar(valor):
    """True si el valor es una plantilla de .env.example (ej. '<region>')."""
    return bool(re.search(r"<[^<>]*>", valor or ""))


# Quien copia .env.example y se olvida de completarlo queda con valores como
# "aws-0-<region>.pooler.supabase.com". Sin este chequeo, cualquier comando
# (migrate, runserver, ...) muere con un error de DNS que no explica nada.
# Si detectamos la plantilla, lo tratamos como "sin configurar" → SQLite.
_valores_db = {
    "DB_HOST": DB_HOST,
    "DB_PORT": os.getenv("DB_PORT", ""),
    "DB_NAME": os.getenv("DB_NAME", ""),
    "DB_USER": os.getenv("DB_USER", ""),
    "DB_PASSWORD": os.getenv("DB_PASSWORD", ""),
}
_sin_completar_en = [nombre for nombre, valor in _valores_db.items() if _sin_completar(valor)]

if DB_HOST and _sin_completar_en:
    warnings.warn(
        "backend/.env tiene valores de ejemplo sin completar ("
        + ", ".join(_sin_completar_en)
        + "). Se usa la SQLite local (db.sqlite3). Completá las credenciales de "
        "Supabase o dejá DB_HOST vacío para desarrollar con SQLite.",
        stacklevel=1,
    )
    DB_HOST = ""

if DB_HOST:
    # PostgreSQL en Supabase. Se recomienda la sección "Session pooler"
    # del dashboard (funciona por IPv4 desde cualquier red).
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "postgres"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": DB_HOST,
            "PORT": os.getenv("DB_PORT", "5432"),
            "OPTIONS": {
                "sslmode": os.getenv("DB_SSLMODE", "require"),
            },
        }
    }
else:
    # Fallback para desarrollar sin credenciales: SQLite local.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


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

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
]
if not CORS_ALLOWED_ORIGINS and DEBUG:
    # Solo para desarrollo: cualquier origen puede llamar a la API.
    CORS_ALLOW_ALL_ORIGINS = True

# Si el frontend necesita enviar cookies/sesiones, descomentar:
# CORS_ALLOW_CREDENTIALS = True
