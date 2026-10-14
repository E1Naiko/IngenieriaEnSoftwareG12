# Ingeniería en Software — Grupo 12

Sistema de gestión de reparto de paquetes (app **core**): backend en **Django**
con base **PostgreSQL en Supabase** y frontend en **React**.

## Estructura

```
frontend/   → app React (la configura el equipo de frontend)
backend/    → API Django + Supabase (ver backend/README.md)
Info/       → documentación del dominio y del esquema de datos
```

## Arranque rápido

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # completar con credenciales de Supabase
python manage.py migrate
python manage.py runserver
```

Instrucciones completas en [backend/README.md](backend/README.md).
Documentación de modelos y decisiones de diseño en [Info/DB.md](Info/DB.md).
