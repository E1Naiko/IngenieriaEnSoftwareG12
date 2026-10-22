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
#Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # completar con credenciales de Supabase
python manage.py migrate
python manage.py runserver
```
#Frontend
```bash
cd frontend
npm install #Instalar todas las dependencias necesarias para que npm pueda ejecutar el front-end correctamente
npm run dev
```

Instrucciones completas en [backend/README.md](backend/README.md).
Documentación de modelos y decisiones de diseño en [Info/DB.md](Info/DB.md).
