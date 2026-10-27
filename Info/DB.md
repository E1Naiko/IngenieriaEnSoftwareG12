# Ingeniería en Software — Grupo 12

Sistema de gestión de reparto de paquetes (app **core**) hecho con **Django** y
**PostgreSQL en Supabase**. Las tablas usan el nombre exacto del diagrama de la
base (`repartidor`, `comercio`, `cliente`, `paquete`, `comprobante`).

## Modelos

| Modelo | Descripción |
|---|---|
| `Repartidor` | Quien entrega. Datos personales + `mail`, `tipo_vehiculo`, `estado` (`activo`/`inactivo`/`baja`) y un `token` de 6 caracteres autogenerado. Sus paquetes: `repartidor.paquetes.all()`. |
| `Comercio` | Comercio que despacha: `nombre`, `telefono` y `direccion`. Tres datos de contacto y nada más. |
| `Cliente` | Datos de contacto del destinatario (teléfono, dirección, DNI). Ya no pertenece a un comercio: el vínculo pasa por `Paquete`. |
| `Paquete` | La entrega: repartidor (opcional), comercio, cliente y comprobante (opcional, uno a uno); incluye las fechas obligatorias `fecha_origen` y `fecha_destino`. `cod_seguimiento` único y autogenerado (`SRFR-XXXXXXXX`). |
| `Comprobante` | Archivo (foto o PDF) de la entrega. La columna `file` es `varchar(255)` y opcional (`null=True`). Se sube a `media/comprobantes/AAAA/MM/`. |

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

> **La base de cada uno tiene que estar al día con `core/migrations/`**:
> corré `python manage.py migrate` antes de programar y `python manage.py
> revisar_db` para comprobar que las tablas coinciden con los modelos. Las
> migraciones de `core` son incrementales y no borran datos, así que no hace
> falta dropear tablas al actualizar.
>
> La migración que agrega `fecha_origen` y `fecha_destino` asigna la fecha del
> momento de la migración a paquetes preexistentes, porque el esquema anterior
> no guardaba esas fechas. Si hay paquetes con datos históricos reales,
> corregí esas dos fechas después de migrar.
>
> Si `migrate` falla con `relation "cliente" already exists` (base creada a
> mano o con las migraciones anteriores borradas), corré primero
> `python manage.py revisar_db`: compara las tablas existentes con los
> modelos, cuenta filas (incluidos los usuarios de `auth_user`) y te dice qué
> hacer. Si las tablas de `core` están vacías, alcanza con
> `drop table if exists paquete, comprobante, cliente, comercio, repartidor cascade;`
> y volver a migrar (no se pierde nada de auth/admin). `migrate --fake-initial`
> solo funciona si las columnas ya coinciden. Ver "Errores comunes" en
> `backend/README.md`.

## Decisiones sobre el esquema

- `repartidor.listado_id_pedidos_asignados` → **no es una columna** (campo
  REVISAR del diagrama): guardar IDs en un string rompe la integridad
  referencial. Es la relación inversa `repartidor.paquetes.all()`; como
  conveniencia existe la property `listado_id_pedidos_asignados`.
- `repartidor.historial_asociado` → mismo criterio: property que devuelve los
  paquetes en estado `entregado` (`repartidor.paquetes.filter(...)`), no una
  lista de IDs serializada en `varchar`.
- **Comercio y cliente son tablas independientes**: no hay FK entre ellas, así
  que cada una se da de alta sola, en cualquier orden. El par comercio ↔
  cliente solo existe dentro de un `Paquete`, que apunta a ambos, y ahí se
  consulta: `Paquete.objects.filter(comercio=c, cliente=k)` (o
  `cliente.paquetes.all()`). Es la forma más simple de modelar "quién le
  despacha a quién" sin atar las dos tablas (HU #37, Ingresar pedido).
- `repartidor.estado` → `activo` / `inactivo` / `baja`. El diagrama deja
  `estado varchar(255)` sin enumerar valores; los tres son los que usa el
  sistema (`baja` es la baja definitiva de la HU #25). Django valida los
  `choices` en los formularios, no en la base, así que la BD acepta cualquier
  varchar(255).
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
- Las tablas conservan el nombre del diagrama vía `Meta.db_table` y las
  claves primarias de estas cinco tablas son enteros de 32 bits. Las columnas
  FK en `paquete` respetan los nombres explícitos del modelo: `id_repartidor_asignado`,
  `id_comercio`, `id_datos_cliente` e `id_comprobante` (configuradas con
  `db_column`). Los nombres de campos de Django siguen `snake_case`; por
  ejemplo, `tipo_vehiculo` y `cod_seguimiento`. `comprobante.file` tiene
  longitud máxima 255.

## Comandos útiles

```bash
python manage.py makemigrations   # genera migraciones tras cambiar models.py
python manage.py migrate          # aplica migraciones a la base
python manage.py revisar_db       # diagnostica tablas viejas vs. modelos
python manage.py shell            # consola interactiva con el ORM
python manage.py runserver        # levanta el servidor de desarrollo
```
