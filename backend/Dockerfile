# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Instalar las dependencias antes de copiar el código aprovecha la caché de Docker.
COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY . .

# La imagen no corre como root. /data aloja el SQLite cuando se usa Compose;
# media y staticfiles quedan disponibles para los volúmenes o el despliegue.
RUN addgroup --system django \
    && adduser --system --ingroup django django \
    && mkdir -p /data /app/media /app/staticfiles \
    && chown -R django:django /app /data

USER django

EXPOSE 8000

# Las migraciones no se ejecutan acá: en producción deben correrse como un paso
# explícito. El Compose de desarrollo sí las ejecuta antes de levantar runserver.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "2", "--timeout", "60", "--access-logfile", "-"]
