# Ingeniería en Software — Grupo 12

Sistema de gestión de reparto de paquetes (app **core**) hecho con **Django**.
La base se separa por entorno en **dos proyectos Supabase/PostgreSQL**: uno de
desarrollo y otro de producción. SQLite queda como alternativa local offline.
Las tablas usan el nombre exacto del diagrama (`repartidor`, `comercio`,
`cliente`, `paquete`, `comprobante`). Para configurar credenciales y trabajar
con cada entorno, ver la [guía de bases por entorno](Ambientes.md).

## Modelos

| Modelo | Descripción |
|---|---|
| `Repartidor` | Quien entrega. Datos personales + `mail`, `tipo_vehiculo`, `estado` (`activo`/`inactivo`/`baja`) y un `token` de 6 caracteres autogenerado. Sus paquetes: `repartidor.paquetes.all()`. |
| `Comercio` | Comercio que despacha: `nombre`, `telefono` y `direccion`. Tres datos de contacto y nada más. |
| `Cliente` | Datos personales y de contacto del destinatario (`nombre`, `apellido`, `telefono`, `direccion`, `dni`). Ya no pertenece a un comercio: el vínculo pasa por `Paquete`. |
| `Paquete` | La entrega: repartidor (opcional), comercio, cliente y comprobante (opcional, uno a uno); incluye las fechas obligatorias `fecha_origen` y `fecha_destino` y los estados `retirado`, `pendiente`, `en_camino`, `entregado` y `cancelado`. `cod_seguimiento` único y autogenerado (`SRFR-XXXXXXXX`). |
| `Comprobante` | Archivo (foto o PDF) de la entrega. La columna `file` es `varchar(255)` y opcional (`null=True`). Se sube a `media/comprobantes/AAAA/MM/`. |

### Estados de un paquete

`Paquete.estado` es un `CharField` con opciones definidas en `Paquete.Estado`:

| Valor guardado | Etiqueta | Constante |
|---|---|---|
| `pendiente` | Pendiente | `Paquete.Estado.PENDIENTE` |
| `retirado` | Retirado | `Paquete.Estado.RETIRADO` |
| `en_camino` | En camino | `Paquete.Estado.EN_CAMINO` |
| `entregado` | Entregado | `Paquete.Estado.ENTREGADO` |
| `cancelado` | Cancelado | `Paquete.Estado.CANCELADO` |

El valor predeterminado sigue siendo `pendiente`. `retirado` debe asignarse
explícitamente, por ejemplo desde el formulario de `/admin/` o desde el ORM:

```python
from core.models import Paquete

paquete = Paquete.objects.get(pk=1)
paquete.estado = Paquete.Estado.RETIRADO
paquete.full_clean()  # valida los campos del modelo, incluido estado
paquete.save(update_fields=["estado"])
```

Los `choices` validan el valor en formularios, el admin y `full_clean()`, pero
`save()` y `objects.create()` **no llaman a `full_clean()` automáticamente**.
El esquema creado por Django tampoco agrega una restricción `CHECK` para las
opciones: SQL directo o `update()` pueden escribir otros valores en la columna
`varchar(255)`. Si la base tiene restricciones agregadas manualmente, hay que
revisarlas por separado.

El modelo no cambia estados automáticamente ni impone transiciones u orden.
El único endpoint de paquetes por ahora es
`GET /api/dashboard/paquetes-en-curso/` (HU #40): excluye solo `entregado`,
comparando el estado sin distinguir mayúsculas. `cancelado` es un estado
intermediario y por eso también se lista. Devuelve `id`, `destinatario`,
`direccion`, `repartidor` y `estado` ("Sin asignar" cuando la FK `repartidor`
es `NULL`). La property
`repartidor.historial_asociado` sigue incluyendo solo paquetes `entregado`;
`retirado` no se considera entregado.

## Puesta en marcha

### 1. Entorno virtual e instalación

```bash
cd backend
python -m venv venv
source venv/bin/activate        # en Windows: venv\Scripts\activate
                                # en Fish: source venv/bin/activate.fish
pip install -r requirements-dev.txt
```

### 2. Mantener dos proyectos Supabase separados

Debe haber un proyecto Supabase para **desarrollo** y otro para **producción**.
Cada proyecto tiene sus propias credenciales (host, usuario y contraseña);
compartir las de desarrollo con el equipo por un gestor seguro y guardar las
de producción únicamente como secretos del hosting. Nunca subirlas al repo.

### 3. Configurar desarrollo

```bash
cd backend
cp .env.example .env
# completar DB_HOST, DB_USER y DB_PASSWORD del proyecto Supabase de desarrollo
python manage.py revisar_db  # comprobar el destino antes de migrar
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

El `.env.example` usa `DATABASE_MODE=postgres`, pero con las credenciales del
proyecto **de desarrollo**. Todo el equipo puede conectarse a ese proyecto; la
base de producción debe tener un host y credenciales distintos. Para ejecutar
la suite de tests localmente sin crear una base de test en Supabase, usar
`DATABASE_MODE=sqlite python manage.py test`.

### 4. Configurar producción

Copiar `.env.supabase.example` como `.env` solo en un entorno de despliegue, o
cargar sus variables como secretos del hosting. Completar las credenciales del
proyecto Supabase **de producción**; mantener `DATABASE_MODE=postgres` y
`DJANGO_DEBUG=False`. No subir el `.env` a Git ni incluirlo en la imagen Docker.

Los datos de los dos proyectos no se sincronizan. Las migraciones crean el
mismo esquema en cada uno, pero los registros de desarrollo no se copian a
producción.

### 5. Migraciones y usuario administrador

`python manage.py migrate` siempre opera sobre la base seleccionada en
`DATABASE_MODE`. Antes de ejecutarlo, comprobar el destino:

```bash
python manage.py revisar_db       # comprobar el destino
python manage.py showmigrations core
python manage.py migrate --plan  # revisar todas las migraciones pendientes
python manage.py migrate
python manage.py showmigrations core  # confirmar que figure [X]
python manage.py createsuperuser  # solo si todavía se necesita un usuario admin
```

Con `backend/.env` configurado para desarrollo, estos comandos apuntan al
Supabase de desarrollo. En un despliegue, apuntan al Supabase de producción;
ejecutar migraciones y crear usuarios allí solo como parte de un despliegue
autorizado. SQLite se usa si se selecciona `DATABASE_MODE=sqlite` o, con
`DJANGO_DEBUG=True`, si no se configura ningún `DATABASE_MODE`; por eso es
importante comprobar el destino antes de migrar.

La migración `core.0006_agregar_estado_retirado_paquete` incorpora `retirado`
al estado de los `choices` de Django. No modifica el tipo ni la longitud de
la columna, no agrega un `CHECK` y no cambia los estados de los paquetes
existentes; no hace falta SQL manual para el esquema generado por Django.
Hay que aplicarla **en cada base** (desarrollo y producción) con `migrate`.
Si hay otras migraciones pendientes, `migrate` también las aplicará: revisar
el plan antes de ejecutarlo. `revisar_db` muestra las migraciones aplicadas,
pero su diagnóstico de columnas no garantiza que todas estén aplicadas; para
confirmar la `0006`, usar `showmigrations core` y buscar `[X]` junto a su nombre.
Si se revierte la `0006`, las filas `retirado` permanecen en la base, pero los
formularios y la validación de la versión anterior no aceptan ese valor.

> **La base de cada entorno tiene que estar al día con `core/migrations/`**:
> corré `python manage.py migrate` antes de programar y `python manage.py
> revisar_db` para comprobar que las tablas coinciden con los modelos. Las
> migraciones son incrementales; la `0006` no requiere borrar tablas ni cambia
> filas existentes. Revisá el plan y respaldá los datos antes de aplicar las
> migraciones pendientes.

> **Antes de cualquier operación destructiva, verificá `python manage.py revisar_db`**
> y asegurate de que el host sea el del proyecto de desarrollo. Nunca ejecutes
> los `DROP` de abajo contra producción.
>
> La migración que agrega `fecha_origen` y `fecha_destino` asigna la fecha del
> momento de la migración a paquetes preexistentes, porque el esquema anterior
> no guardaba esas fechas. Si hay paquetes con datos históricos reales,
> corregí esas dos fechas después de migrar. Del mismo modo, la migración que
> agrega `nombre` y `apellido` a `cliente` completa valores iniciales en los
> clientes preexistentes para cumplir `NOT NULL`.
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
