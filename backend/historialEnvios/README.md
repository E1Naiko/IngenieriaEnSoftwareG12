# historialEnvios — Ver historial de envíos (HU #10)

Endpoints para que el **coordinador** vea el historial de envíos de cada repartidor.
El historial se consulta en **dos pasos**: primero la lista de repartidores y, al elegir uno,
el listado con todos sus pedidos.

> **Ubicación:** `backend/historialEnvios/`
> **Modelos usados:** `core.models.Repartidor` y `core.models.Paquete` (esta app no tiene modelos ni migraciones propias).
> **Rutas:** `GET /api/historial/` y `GET /api/historial/<id>/` (montadas en `config/urls.py → api/`)

El historial **no se guarda en ninguna tabla**: se arma en el momento leyendo la tabla `paquete`
y filtrando los pedidos ya terminados.

---

## 1. Qué entra en el historial

Los paquetes de un repartidor cuyo estado es **`entregado`** o **`cancelado`**, sin distinguir
mayúsculas de minúsculas (`ENTREGADO`, `Entregado` y `entregado` valen igual).

Los paquetes `pendiente`, `retirado` y `en_camino` **no** aparecen: todavía no terminaron.

Los repartidores **dados de baja también se listan**, porque conservan su historial.

Los estados que cuentan están en una sola constante de `views.py`:

```python
ESTADOS_HISTORIAL = ["entregado", "cancelado"]

```

---

## 2. Contrato de la API

Los dos endpoints son de solo lectura (`GET`) y **requieren sesión iniciada**. Como hay un único
coordinador, alcanza con estar logueado.

### Paso 1 — Lista de repartidores

```
GET /api/historial/
```

```json
{
  "results": [
    {
      "id": 1,
      "nombre": "Ana",
      "apellido": "Paz",
      "dado_de_baja": false,
      "cantidad_envios": 4
    }
  ],
  "count": 1
}
```

- `cantidad_envios` cuenta los pedidos del historial de ese repartidor (entregados + cancelados).
- `dado_de_baja` es `true` si el repartidor tiene estado `baja`. El estado `activo` / `inactivo` **no se
  devuelve** porque cambia según su disponibilidad y no aporta al historial.
- Los repartidores salen ordenados por apellido y nombre.

### Paso 2 — Historial de un repartidor

```
GET /api/historial/<id>/
```

```json
{
  "repartidor": {
    "id": 1,
    "nombre": "Ana",
    "apellido": "Paz",
    "dado_de_baja": false
  },
  "results": [
    {
      "id": 12,
      "cod_seguimiento": "SRFR-1A2B3C4D",
      "estado": "entregado",
      "fecha_origen": "2026-10-20",
      "fecha_destino": "2026-10-22",
      "comercio": "Kiosco Sur",
      "cliente": "Gómez, Laura",
      "direccion": "Calle 123"
    }
  ],
  "count": 1
}

```

- Los pedidos salen del **más reciente al más viejo**: primero por `fecha_destino` y, si empatan, por `id`.
- Un repartidor sin pedidos terminados devuelve `"results": []` y `"count": 0`.

### Respuestas

| Caso | Código | Respuesta |
|---|---|---|
| Listado correcto | `200` | Ver los ejemplos de arriba |
| Sin sesión iniciada | `401` | `{"message": "Solo el coordinador puede ver el historial."}` |
| El repartidor no existe | `404` | `{"message": "Repartidor no encontrado."}` |
| Cualquier método que no sea `GET` | `405` | sin cuerpo |
| `<id>` que no es un número (ej. `/historial/abc/`) | `404` | Lo rechaza Django antes de llegar a la vista, por usar `<int:pk>` |

---

## 3. Cómo funciona

1. Cada vista controla primero la sesión (`_solo_coordinador`). Si no hay usuario logueado, responde `401`.
2. **Lista:** trae todos los repartidores y les agrega un campo calculado `cantidad_envios` con
   `Count("paquetes", filter=...)`, usando el filtro de estados.
3. **Detalle:** busca al repartidor con `Repartidor.objects.filter(pk=pk).first()` (si es `None`, `404`),
   toma sus paquetes (`repartidor.paquetes`), aplica el filtro de estados y los ordena.
4. `select_related("comercio", "cliente")` trae el comercio y el cliente en la misma consulta,
   para no hacer una consulta extra por cada paquete.
5. `_q_estados()` arma el filtro de estados. `__iexact` acepta un solo valor, así que se genera
   un filtro por cada estado y se unen con OR.

---

## 4. Estructura

```
historialEnvios/
├── __init__.py
├── apps.py        # AppConfig
├── views.py       # historial_lista, historial_repartidor + helpers
├── urls.py        # rutas historial/ e historial/<int:pk>/
├── tests.py
└── README.md      # este archivo
```

Dependencias:

```
historialEnvios.views  →  core.models.Repartidor (y su relación inversa paquetes)
config/urls.py         →  historialEnvios.urls  (include "/api/")
config/settings.py     →  "historialEnvios" en INSTALLED_APPS
```

`models.py` y `admin.py` quedaron como los generó `startapp`, sin cambios.

---

## 5. Tests

```bash
cd backend
python manage.py test historialEnvios
```

Casos que cubren los tests:

| Caso | Qué verifica |
|---|---|
| Lista de repartidores | `200`, aparecen todos (también uno dado de baja) con su `cantidad_envios` |
| Historial de un repartidor | `200`, aparecen sus pedidos `entregado` y `cancelado` |
| Pedidos que no entran | Un paquete `pendiente` no aparece en el historial ni en el conteo |
| Sin sesión | Los dos endpoints responden `401` |
| Repartidor inexistente | `404` |

### Probarlo a mano

1. Con `python manage.py runserver` corriendo, iniciá sesión en `http://127.0.0.1:8000/admin/`.
2. En el mismo navegador abrí `http://127.0.0.1:8000/api/historial/` y después
   `http://127.0.0.1:8000/api/historial/<id>/` con el id de un repartidor.
3. Cerrá sesión y repetí: tiene que responder `401`.

---

## 6. Limitaciones y pendientes

- **Reasignación de pedidos.** El historial se arma con el repartidor que el paquete tiene asignado
  **hoy** (`paquete.repartidor`). Si más adelante un pedido se reasigna (HU #11), el repartidor anterior
  deja de verlo en su historial. Resolverlo requiere guardar un registro de cada intento
  (paquete, repartidor, estado, fecha), algo que el modelo actual no tiene. Lo mismo pasa si se borra un
  repartidor: la clave foránea es `SET_NULL` y sus paquetes quedan sin repartidor.
- **Motivo de cancelación.** El modelo `Paquete` todavía no tiene un campo para el motivo. Los pedidos
  cancelados aparecen en el historial con `"estado": "cancelado"` y nada más. Cuando se implemente la
  cancelación del paquete (HU #13) y exista la columna, se agrega a `_paquete_to_dict` (ya hay un
  comentario `TODO` en `views.py`).
- **Criterio de ordenamiento.** Se ordena por `fecha_destino`, que hoy es solo una fecha. Confirmar si
  representa la fecha de entrega real o la prevista.
- **Definición de historial.** `Repartidor.historial_asociado` (`core/models.py`) y `Info/DB.md` todavía
  dicen que el historial incluye solo los `entregado`. Esta app incluye también los `cancelado`, por lo que
  esos dos lugares quedarían desactualizados.
- **Formato de errores.** Se usa la clave `message`, igual que `loginCoordinador` y `loginRepartidor`.
  Otras apps del proyecto usan `detail` para los `404`.
