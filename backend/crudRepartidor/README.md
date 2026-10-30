# crudRepartidor — Alta de repartidor (HU #25)

Endpoint para que el **coordinador** dé de alta un repartidor. El sistema le genera
automáticamente su **token de acceso** (el que después usa para iniciar sesión, HU #9).

> **Ubicación:** `backend/crudRepartidor/`
> **Modelo de datos:** `core.models.Repartidor` (no tiene modelos ni migraciones propias).
> **Ruta:** `POST /api/repartidores/` (montada en `config/urls.py → api/`)

Por ahora la app implementa **solo el alta (Create)**. Listar, editar y borrar repartidores
no forman parte de esta historia.

---

## 1. Contrato de la API

```
POST /api/repartidores/
Content-Type: application/json

{
  "dni": "30111222",
  "nombre": "Ana",
  "apellido": "Paz",
  "telefono": "1155550000",
  "mail": "ana@mail.com",
  "tipo_vehiculo": "moto"
}
```

Los seis campos son **obligatorios**. El `token` y el `estado` no se mandan: los define el sistema.

`tipo_vehiculo` tiene que ser uno de los valores de `Repartidor.TipoVehiculo`:

| Valor | ¿Esta en el modelo? |
|---|---|
| `moto` | si |
| `auto` | si |
| `camioneta` | si |
| `camion` | **pendiente de agregar en el modelo** (ver sección 5). Hasta entonces la API lo rechaza con "Tipo de vehículo inválido". |

| Caso (escenario de la HU) | Código | Respuesta |
|---|---|---|
| 1. Alta exitosa | `201` | `{"message": "Repartidor cargado con éxito", "repartidor": {...}}` |
| 2. Campo en blanco | `400` | `{"<campo>": "Campo obligatorio"}` |
| 3. Dato repetido (DNI, mail o teléfono) | `400` | `{"<campo>": "Este dato ya existe en el sistema"}` |
| El DNI no es un número | `400` | `{"dni": "El DNI debe ser un número"}` |
| `tipo_vehiculo` no permitido | `400` | `{"tipo_vehiculo": "Tipo de vehículo inválido"}` |
| El cuerpo no es JSON | `400` | `{"message": "El cuerpo debe ser JSON válido."}` |
| Cualquier método que no sea `POST` | `405` | sin cuerpo |

- Los errores de validación llegan como un objeto `{campo: mensaje}` y **pueden venir varios a la vez**,
  así el front marca cada campo con su mensaje.
- En el `201`, el token generado viene en `repartidor.token`.

Ejemplo de respuesta exitosa:

```json
{
  "message": "Repartidor cargado con éxito",
  "repartidor": {
    "id": 1,
    "nombre": "Ana",
    "apellido": "Paz",
    "dni": 30111222,
    "telefono": "1155550000",
    "mail": "ana@mail.com",
    "tipo_vehiculo": "moto",
    "estado": "activo",
    "token": "A7K2Q9"
  }
}
```

---

## 2. Cómo funciona

1. Lee el JSON del cuerpo (`_parse_body`). Si no es válido, responde `400`.
2. Valida los datos (`_validar_alta`) y junta **todos** los errores en un diccionario:
   - Ningún campo puede estar vacío.
   - El DNI tiene que ser numérico y no existir ya.
   - El mail y el teléfono no pueden existir ya.
   - El tipo de vehículo tiene que ser uno de los permitidos por el modelo.
3. Si hay errores, responde `400` con ese diccionario.
4. Si no, crea el repartidor con `Repartidor.objects.create(...)`. El **token se genera solo**: lo crea
   el modelo (`core/models.py`) al guardar por primera vez (6 caracteres, letras mayúsculas y números,
   único).
5. Responde `201` con el mensaje de la HU y los datos del repartidor.

### Decisiones

- **El token lo genera el modelo, no la vista.** Está en `Repartidor.save()` / `_generar_token()`.
- **El token se devuelve en la respuesta** y **no se envía por mail**. La HU lo menciona, pero por ahora
  el envío por mail no está implementado.
- **Mail y teléfono se validan por código.** En la base solo `dni` y `token` son únicos; la unicidad de
  mail y teléfono la controla `_validar_alta`.
- **Tipos de vehículo:** la validación compara contra `Repartidor.TipoVehiculo.values`, así que no hay
  que tocar la vista cuando se agrega un tipo nuevo al modelo.
- **`IntegrityError`:** si dos altas con el mismo DNI llegan al mismo tiempo, la base lo frena y se
  responde como dato repetido.
- **Sin DRF:** igual que `crudComercios`, usa `JsonResponse` y `json.loads`, sin Django REST Framework.
- **`@csrf_exempt`** y **`@require_POST`**, como el resto de la API.
- **Estado inicial:** el repartidor queda con el estado por defecto del modelo (`activo`).

---

## 3. Estructura

```
crudRepartidor/
├── __init__.py
├── apps.py        # AppConfig
├── views.py       # repartidores_alta + helpers (_parse_body, _repartidor_to_dict, _validar_alta)
├── urls.py        # ruta repartidores/
├── tests.py       # 3 tests (un escenario de la HU cada uno)
└── README.md      # este archivo
```

Dependencias:

```
crudRepartidor.views  →  core.models.Repartidor
config/urls.py        →  crudRepartidor.urls  (include "/api/")
config/settings.py    →  "crudRepartidor" en INSTALLED_APPS
```

---

## 4. Tests

```bash
cd backend
python manage.py test crudRepartidor
```

| Test | Escenario |
|---|---|
| `test_escenario_1_alta_exitosa` | 201, mensaje de la HU, el repartidor queda en la base con su token |
| `test_escenario_2_campo_en_blanco` | 400 con "Campo obligatorio" y no se crea nada |
| `test_escenario_3_dato_repetido` | 400 con "Este dato ya existe en el sistema" |

> Para probar sin tocar la base de Supabase, dejá `DB_HOST=` vacío en tu `.env`: Django usa una
> SQLite temporal.

### Probarlo a mano (PowerShell)

Con `python manage.py runserver` corriendo:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/repartidores/ -Method Post -ContentType "application/json" -Body '{"dni":"30111222","nombre":"Ana","apellido":"Paz","telefono":"1155550000","mail":"ana@mail.com","tipo_vehiculo":"moto"}' | ConvertTo-Json -Depth 5
```

---

## 5. Pendiente / a confirmar con el equipo

- **Agregar `camion` a `Repartidor.TipoVehiculo`** en `core/models.py` (por ejemplo
  `CAMION = "camion", "Camión"`) y generar la migración. Es un cambio del modelo, así que lo hace quien
  mantiene `core`. La vista no necesita cambios: apenas esté en el modelo, la API lo acepta.
- Si el repartidor tiene que arrancar `activo` o `inactivo` hasta que se ponga "Disponible" él mismo.
- Si mail y teléfono tienen que ser únicos también en el modelo.