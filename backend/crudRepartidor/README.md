# crudRepartidor — Alta y edición de repartidor (HU #25 y HU #39)

Endpoints para que el **coordinador** dé de alta y edite repartidores. Al dar de alta, el sistema genera
automáticamente su **token de acceso** (el que después usa para iniciar sesión, HU #9). Al editar, el
token **se mantiene**.

> **Ubicación:** `backend/crudRepartidor/`
> **Modelo de datos:** `core.models.Repartidor` (no tiene modelos ni migraciones propias).
> **Rutas** (montadas en `config/urls.py → api/`):
> - `POST /api/repartidores/` → alta (HU #25)
> - `GET` y `PUT /api/repartidores/<id>/` → ver y editar (HU #39)

Por ahora la app implementa **alta y edición**. Listar y dar de baja repartidores no forman parte de
estas historias.

---

## 1. Alta de repartidor (HU #25)

### Contrato de la API

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

| Valor | ¿Está en el modelo? |
|---|---|
| `moto` | sí |
| `auto` | sí |
| `camioneta` | sí |
| `camion` | sí |

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
    "estado": "ACTIVO",
    "token": "A7K2Q9"
  }
}
```

---

## 2. Edición de repartidor (HU #39)

El front arma el formulario con un `GET` (precarga los datos) y guarda con un `PUT`. El `<id>` lo toma
de la lista desde donde el coordinador hace clic en "Editar repartidor".

### Ver los datos para precargar el formulario

```
GET /api/repartidores/<id>/
```

```json
{
  "repartidor": {
    "nombre": "Ana",
    "apellido": "Paz",
    "dni": 30111222,
    "telefono": "1155550000",
    "mail": "ana@mail.com",
    "tipo_vehiculo": "moto",
    "token": "A7K2Q9"
  }
}
```

Devuelve **solo los datos de la HU**: no incluye el `id` (el front ya lo tiene, lo usó en la URL) ni el
`estado`. El token se muestra pero no se edita.

### Guardar los cambios

```
PUT /api/repartidores/<id>/
Content-Type: application/json

{
  "dni": 30111222,
  "nombre": "Ana",
  "apellido": "Paz",
  "telefono": "1155550000",
  "mail": "ana@mail.com",
  "tipo_vehiculo": "auto"
}
```

Se mandan los seis campos editables (todos obligatorios). El `token` y el `estado` **no se envían ni se
modifican**.

| Caso (escenario de la HU) | Código | Respuesta |
|---|---|---|
| 1. Edición exitosa | `200` | `{"message": "Repartidor modificado con éxito"}` |
| 2. Campo en blanco | `400` | `{"<campo>": "Campo obligatorio"}` |
| 3. Dato repetido (DNI, mail o teléfono de **otro** repartidor) | `400` | `{"<campo>": "Este dato ya existe en el sistema"}` |
| El DNI no es un número | `400` | `{"dni": "El DNI debe ser un número"}` |
| `tipo_vehiculo` no permitido | `400` | `{"tipo_vehiculo": "Tipo de vehículo inválido"}` |
| El cuerpo no es JSON | `400` | `{"message": "El cuerpo debe ser JSON válido."}` |
| El repartidor no existe | `404` | `{"message": "Repartidor no encontrado."}` |
| Cualquier otro método (ni `GET` ni `PUT`) | `405` | sin cuerpo |

- Los errores de validación tienen el mismo formato que en el alta (`{campo: mensaje}`, varios a la vez).
- Guardar un repartidor **con sus propios datos** no cuenta como repetido.
- Al guardar, el nombre y el apellido se normalizan (primera letra de cada palabra en mayúscula) y el mail
  se pasa a minúscula, igual que en el alta. Conviene que el front refresque los datos después de guardar.
- El `PUT` responde solo el mensaje: no devuelve los datos del repartidor.

---

## 3. Cómo funciona

1. Lee el JSON del cuerpo (`_parse_body`). Si no es válido, responde `400`.
2. Valida los datos (`_validar_datos`) y junta **todos** los errores en un diccionario:
   - Ningún campo puede estar vacío.
   - El DNI tiene que ser numérico y no existir ya.
   - El mail y el teléfono no pueden existir ya.
   - El tipo de vehículo tiene que ser uno de los permitidos por el modelo.
3. Si hay errores, responde `400` con ese diccionario.
4. **Alta:** crea el repartidor con `Repartidor.objects.create(...)`. El **token se genera solo**: lo crea
   el modelo (`core/models.py`) al guardar por primera vez (6 caracteres, letras mayúsculas y números,
   único). Responde `201` con el mensaje de la HU y los datos del repartidor.
5. **Edición:** busca el repartidor por `pk` (`404` si no existe), valida con
   `_validar_datos(data, excluir_pk=repartidor.pk)`, actualiza solo los seis campos editables y guarda.
   Responde `200` con el mensaje de la HU.

### Decisiones

- **El token lo genera el modelo, no la vista.** Está en `Repartidor.save()` / `_generar_token()`.
- **El token se mantiene al editar.** Es la credencial con la que el repartidor inicia sesión: regenerarlo
  cada vez que se edita cualquier dato le quitaría el acceso.
- **El token se devuelve en el alta** y **no se envía por mail**. La HU lo menciona, pero por ahora
  el envío por mail no está implementado.
- **La misma validación para alta y edición.** `_validar_datos` recibe `excluir_pk`: en la edición se
  excluye al propio repartidor de la búsqueda de repetidos, para que no choque consigo mismo.
- **El `GET` de edición no devuelve `id` ni `estado`:** se devuelve solo lo que el front necesita
  (los campos de la HU #39). Las respuestas del alta no se modificaron.
- **El estado no se toca al editar.** Editar los datos no activa ni desactiva al repartidor.
- **Mail y teléfono se validan por código.** En la base solo `dni` y `token` son únicos; la unicidad de
  mail y teléfono la controla `_validar_datos`.
- **Tipos de vehículo:** la validación compara contra `Repartidor.TipoVehiculo.values`, así que no hay
  que tocar la vista cuando se agrega un tipo nuevo al modelo.
- **`IntegrityError`:** si dos altas (o ediciones) con el mismo DNI llegan al mismo tiempo, la base lo
  frena y se responde como dato repetido.
- **Sin DRF:** igual que `crudComercios`, usa `JsonResponse` y `json.loads`, sin Django REST Framework.
- **`@csrf_exempt`** y **`@require_POST`** / **`@require_http_methods`**, como el resto de la API.
- **Estado inicial:** el repartidor queda con el estado por defecto del modelo (`ACTIVO`).

---

## 4. Estructura

```
crudRepartidor/
├── __init__.py
├── apps.py        # AppConfig
├── views.py       # repartidores_alta, repartidor_detalle + helpers
│                  #   (_parse_body, _repartidor_to_dict, _repartidor_edicion_to_dict, _validar_datos)
├── urls.py        # rutas repartidores/ y repartidores/<int:pk>/
├── tests.py       # alta (4 tests) y edición (10 tests)
└── README.md      # este archivo
```

Dependencias:

```
crudRepartidor.views  →  core.models.Repartidor
config/urls.py        →  crudRepartidor.urls  (include "/api/")
config/settings.py    →  "crudRepartidor" en INSTALLED_APPS
```

---

## 5. Tests

Los tests tienen que correr con SQLite, para no crear bases de prueba en Supabase:

```powershell
cd backend
$env:DATABASE_MODE="sqlite"
python manage.py test crudRepartidor
Remove-Item Env:DATABASE_MODE
```

**Alta (HU #25)**

| Test | Qué verifica |
|---|---|
| `test_escenario_1_alta_exitosa` | 201, mensaje de la HU, el repartidor queda en la base con su token |
| `test_escenario_2_campo_en_blanco` | 400 con "Campo obligatorio" y no se crea nada |
| `test_escenario_3_dato_repetido` | 400 con "Este dato ya existe en el sistema" |
| `test_nombre_y_apellido_se_guardan_con_mayuscula_inicial` | Normaliza el nombre y el apellido, y pasa el mail a minúscula |

**Edición (HU #39)**

| Test | Qué verifica |
|---|---|
| `test_escenario_1_edicion_exitosa` | 200, mensaje de la HU, cambios guardados (normalizados) y el token se mantiene |
| `test_escenario_2_campo_en_blanco` | 400 con "Campo obligatorio" y no se modifica nada |
| `test_escenario_3_dato_repetido` | 400 con "Este dato ya existe" en DNI, mail y teléfono de otro repartidor |
| `test_guardar_con_sus_propios_datos_no_es_repetido` | Guardar sin cambiar el DNI, mail o teléfono no da error |
| `test_dni_no_numerico` | 400 con "El DNI debe ser un número" |
| `test_tipo_vehiculo_invalido` | 400 con "Tipo de vehículo inválido" |
| `test_json_invalido` | 400 si el cuerpo no es JSON |
| `test_repartidor_inexistente` | 404 con "Repartidor no encontrado." |
| `test_get_devuelve_solo_los_datos_de_la_hu` | El `GET` devuelve los 7 campos, sin `id` ni `estado` |
| `test_metodo_no_permitido` | 405 con un método que no es `GET` ni `PUT` |

### Probarlo a mano (PowerShell)

Con `python manage.py runserver` corriendo. Ojo: si tu `.env` apunta a Supabase, probá con un repartidor
de prueba tuyo, porque estás modificando la base compartida.

```powershell
# Alta
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/repartidores/ -Method Post -ContentType "application/json" -Body '{"dni":"30111222","nombre":"Ana","apellido":"Paz","telefono":"1155550000","mail":"ana@mail.com","tipo_vehiculo":"moto"}' | ConvertTo-Json -Depth 5

# Ver los datos de un repartidor (también se puede abrir en el navegador)
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/repartidores/1/ | ConvertTo-Json -Depth 5

# Editar
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/repartidores/1/ -Method Put -ContentType "application/json" -Body '{"dni":30111222,"nombre":"Ana","apellido":"Paz","telefono":"1155550000","mail":"ana@mail.com","tipo_vehiculo":"auto"}'
```

---

## 6. Pendiente / a confirmar con el equipo

- Qué lista usa el front para el botón "Editar repartidor" y si esa lista incluye a los repartidores
  inactivos o dados de baja.

---