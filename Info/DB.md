# Ingeniería en Software — Grupo 12

Sistema de gestión de reparto de paquetes (app **core**) hecho con **Django** y
**PostgreSQL en Supabase**. Las tablas usan el nombre exacto del diagrama de la
base (`repartidor`, `comercio`, `cliente`, `paquete`, `comprobante`).

## Modelos

| Modelo | Descripción |
|---|---|
| `Repartidor` | Quien entrega. Datos + `mail`, `estado` (activo/inactivo/suspendido) y `token` de 6 caracteres autogenerado. Sus paquetes: `repartidor.paquetes.all()`. |
| `Comercio` | Comercio que despacha. Puede referenciar un `datos_cliente` (`id_datos_cliente` del diagrama). |
| `Cliente` | Datos de contacto del destinatario (teléfono, dirección, DNI único), atado a un comercio (`id_comercio`). |
| `Paquete` | La entrega: repartidor (opcional), comercio, cliente y comprobante (opcional, uno a uno). `cod_seguimiento` único y autogenerado (`SRFR-XXXXXXXX`). |
| `Comprobante` | Archivo (foto/PDF) de la entrega. `file` es opcional según el diagrama. |

## Puesta en marcha

### 1. Entorno virtual e instalación

```bash
cd backend
python -m venv venv
source venv/bin/activate        # en Windows: venv\Scripts\activate
                                # en Fish: source venv/bin/activate.fish
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
cd backend
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

> **OJO**: si ya habías corrido `migrate` con el esquema anterior, borra tu
> `db.sqlite3` local (o dropeá el schema `public` en Supabase) y volvé a
> correr `migrate`: la estructura cambió y las migraciones se regeneraron.

## Decisiones sobre el esquema

- `repartidor.listado_id_pedidos_asignados` → **no es una columna** (campo
  REVISAR del diagrama): guardar IDs en un string rompe la integridad
  referencial. Es la relación inversa `repartidor.paquetes.all()`; como
  conveniencia existe la property `listado_id_pedidos_asignados`.
- `repartidor.historial_asociado` → mismo criterio: property que devuelve los
  paquetes en estado `entregado` (`repartidor.paquetes.filter(...)`).
- **Ciclo comercio ↔ cliente**: el diagrama pide `comercio.id_datos_cliente`
  y `cliente.id_comercio` ambos `not null`, pero eso hace imposible insertar
  el primer registro (cada tabla necesita a la otra). Se resolvió dejando
  `comercio.id_datos_cliente` **nullable**: se crea comercio → cliente → se
  linkea. Es el único desvío respecto al diagrama.
- `paquete ?<>? repartidor` → FK `paquete.repartidor` opcional
  (`SET_NULL`): un paquete tiene a lo sumo un repartidor; un repartidor,
  muchos paquetes.
- `paquete.id_comprobante ?>? comprobante` → **uno a uno** modelado desde
  `Paquete` (columna `paquete.id_comprobante`), nullable: el comprobante se
  carga cuando se entrega el paquete. `comprobante.file` es nullable, como
  en el diagrama.
- `paquete.codSeguimiento` → único y **autogenerado** al crear
  (`SRFR-XXXXXXXX`, entra en el `varchar(255)` del diagrama).
- `cliente.dni` y `repartidor.dni` → enteros **únicos** (un DNI identifica
  una persona; el diagrama no lo marca pero es la interpretación correcta).
- Los campos de opciones (`tipoVehiculo`, `estado` de repartidor y paquete,
  `tamanio`) usan `choices` de Django: los valores del enum se revisan y
  agregan fácil en `backend/core/models.py`.
- Nombres de **columnas** en `snake_case` (convención Django): el
  `tipoVehiculo` del diagrama es `tipo_vehiculo`, `codSeguimiento` es
  `cod_seguimiento`, etc. Las tablas conservan el nombre del diagrama vía
  `Meta.db_table`.

## Comandos útiles

```bash
python manage.py makemigrations   # genera migraciones tras cambiar models.py
python manage.py migrate          # aplica migraciones a la base
python manage.py shell            # consola interactiva con el ORM
python manage.py runserver        # levanta el servidor de desarrollo
```
