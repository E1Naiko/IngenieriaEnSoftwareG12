# Ingeniería en Software — Grupo 12

Sistema de gestión de reparto de paquetes (app `SRFR`) hecho con **Django** y
**PostgreSQL en Supabase**.

## Modelos

| Modelo | Descripción |
|---|---|
| `Repartidor` | Quien entrega. Tiene muchos paquetes asignados (`repartidor.paquetes.all()`). |
| `Comercio` | Comercio que despacha paquetes. |
| `Cliente` | Destinatario (DNI único). |
| `Paquete` | La entrega: vincula repartidor (opcional), comercio, cliente y comprobante. Código de seguimiento único y autogenerado (`SRFR-XXXXXXXX`). |
| `Comprobante` | Archivo (foto/PDF) que acredita la entrega. |

## Puesta en marcha

### 1. Entorno virtual e instalación

```bash
python -m venv venv
source venv/bin/activate        # en Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Crear el proyecto en Supabase (una sola persona del grupo)

1. Entrar a https://supabase.com y crear una organización y un proyecto
   (guardar la **contraseña de la base de datos** que pide al crearlo).
2. En el dashboard, botón **Connect** (barra superior) → sección
   **"Session pooler"**: ahí están el host, puerto, usuario y nombre de base.
3. Pasar esos valores al equipo (por privado, no por el repo).

### 3. Configurar credenciales (cada integrante)

```bash
cp .env.example .env
# y editar .env con los valores de Supabase
```

> Si alguien no tiene las credenciales a mano, puede dejar el `.env` vacío y
> Django usará una SQLite local (`db.sqlite3`) para seguir desarrollando.

### 4. Crear las tablas y un usuario administrador

```bash
python manage.py migrate            # crea las tablas en la base
python manage.py createsuperuser    # usuario para entrar al /admin
python manage.py runserver
```

Entrar a http://127.0.0.1:8000/admin/ con el superusuario y ya se pueden
cargar repartidores, comercios, clientes y paquetes.

## Decisiones sobre el esquema original (los "// REVISAR")

- `repartidor.listado_id_pedidos_asignados` → **no es una columna**: guardar
  IDs en un string rompe la integridad referencial. Los paquetes de un
  repartidor salen de la relación inversa: `repartidor.paquetes.all()`.
- `repartidor.historial_asociado` → mismo criterio: es una consulta sobre los
  paquetes del repartidor, no una columna. Cuando definan estados de paquete
  (pendiente/entregado) el historial va a ser un `filter(...)`.
- La referencia `paquete ?<>? repartidor` se modeló como **uno a muchos**
  (un paquete tiene a lo sumo un repartidor; un repartidor, muchos paquetes),
  que es lo que indicaba la columna `id_repartidor_asignado`.
- `paquete.codSeguimiento` → único y **autogenerado** al crear el paquete.
- `cliente.dni` → entero, **único**.
- `comprobante.file` → `FileField` real (los archivos van a `media/`).
  Próximo paso sugerido: guardarlos en **Supabase Storage** con
  `django-storages` en lugar del disco local.
- Los campos de opciones (`tipoVehiculo`, `estado`, `tamanio`) usan
  `choices`: revisar que los valores del enum les sirvan (se agregan fácil
  en `SRFR/models.py`).

## Comandos útiles

```bash
python manage.py makemigrations   # genera migraciones tras cambiar models.py
python manage.py migrate          # aplica migraciones a la base
python manage.py shell            # consola interactiva con el ORM
python manage.py runserver        # levanta el servidor de desarrollo
```
