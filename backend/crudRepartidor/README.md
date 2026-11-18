# crudRepartidor — Alta y edición de repartidor (HU #25 y HU #39)

Endpoints para que el **coordinador** dé de alta y edite repartidores. Al dar de alta, el sistema genera
automáticamente su **token de acceso** (el que después usa para iniciar sesión, HU #9). Al editar, el
token **se mantiene**.

> **Ubicación:** `backend/crudRepartidor/`
> **Modelo de datos:** `core.models.Repartidor` (no tiene modelos ni migraciones propias).
> **Rutas** (montadas en `config/urls.py → api/`):
> - `POST /api/repartidores/` → alta (HU #25)
> - `GET /api/repartidores/lista/` → lista de repartidores para elegir a quién editar (HU #39)
> - `GET` y `PUT /api/repartidores/<id>/` → ver y editar (HU #39)

Por ahora la app implementa **alta y edición**, con una lista mínima para elegir a quién editar. Dar de
baja repartidores no forma parte de estas historias.

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

El front arma el formulario con un