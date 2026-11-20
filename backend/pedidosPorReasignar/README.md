# Pedidos "Por Reasignar" (HU #36)

> **Como** repartidor **quiero** ver la lista de pedidos "Por Reasignar" que otro
> repartidor no pudo completar **para** poder tomar alguno aunque ya tenga otro
> pedido asignado.

App sin modelos propios y **sin cambios en el esquema**: no hay estado nuevo,
ni campos nuevos, ni migración. Todo se lee de `core.models.Paquete`.

## Cómo se publica un pedido (sin estado nuevo)

El botón **"Confirmar cancelación"** de `Dashboardrepartidor.tsx` llama a
`POST /api/cambiar-estado-pedido/` con `{"estado": "cancelado", "motivo": ...}`.
Ese endpoint (HU #34) **no limpia** `paquete.repartidor`, así que el pedido
queda `cancelado` con la FK apuntando al último repartidor que lo tuvo.

Por eso:

- **La lista = todos los `Paquete` en estado `cancelado`** (comparación
  `iexact`, porque la base de desarrollo tiene estados en mayúsculas).
- **"La última persona que lo retiró" se muestra directamente** con el nombre
  y apellido de `paquete.repartidor`, sin una tabla de historial ni un snapshot.
  Si el pedido nunca tuvo repartidor, el campo vale `null`.

Esto coincide con el comentario que ya estaba en `pedidosAsignados/views.py`:
*"entregado y cancelado ya no son suyos (el cancelado pasa a pedidos
cercanos)"*. No se agregó el estado `por_reasignar` ni los campos
`fue_retirado` / `retirado_por` que se habían probado antes.

| Regla de la HU | Cómo se resuelve |
| --- | --- |
| Ingresó con su token único y está "Operativo" | El token viaja en el body de **cada** request (no hay sesión; el front lo guarda en `localStorage`). "Operativo" = `ACTIVO` (`Repartidor.Estado`, migración 0009); se toleran `DISPONIBLE` y `OPERATIVO` de datos legados. 404 token inválido, 403 no operativo. |
| Solo pedidos publicados en zona cercana | **La zona cercana quedó descartada**: entran todos los `cancelado`, sin filtro geográfico ni por capacidad del vehículo. |
| Puede tomarlo aunque ya tenga otros asignados | No hay ningún chequeo sobre la cantidad de pedidos del repartidor. |
| Cada pedido muestra solo lo necesario | `direccion_retiro`, `direccion_destino`, `tamanio` y `ultimo_repartidor` (nombre y apellido). No se expone destinatario ni estado. |
| Un solo repartidor; desaparece de las otras listas | `UPDATE` condicional con `estado=cancelado` en el `WHERE`, dentro de `transaction.atomic()`. Quien llega segundo actualiza 0 filas → 409. |
| Al tomarlo se agrega a sus asignados | El aceptar setea `repartidor` y `estado=asignado`; con eso ya aparece en `POST /api/paquetes-repartidor/` (HU #17), que lista `repartidor.paquetes`. |

`direccion_retiro` es hoy `comercio.direccion`: el modelo no guarda la posición
del repartidor anterior. Cuando se implemente "ubicación actual", se cambia la
serialización sin tocar el contrato de los otros campos.

## Endpoints

Montados bajo `/api/` en `config/urls.py`; son `POST` con `@csrf_exempt`
(el front del repartidor no maneja token CSRF).

### `POST /api/pedidos-por-reasignar/`

Body: `{"token": "ABC123"}`.

```json
// 200 con pedidos (escenario 1)
{
  "pedidos": [
    {
      "id": 17,
      "direccion_retiro": "Calle 1 #23",
      "direccion_destino": "Calle 2 #45",
      "tamanio": "mediano",
      "ultimo_repartidor": { "nombre": "Marta", "apellido": "López" }
    }
  ]
}

// 200 sin pedidos (escenario 2)
{ "mensaje": "No hay pedidos pendientes de reasignación.", "pedidos": [] }
```

`ultimo_repartidor` es `null` si la FK `repartidor` está vacía. La consulta usa
`select_related("cliente", "comercio", "repartidor")` para evitar N+1.
Otros códigos: `400` (body inválido / falta token), `404` (sesión inválida),
`403` (inactivo o baja), `405` (GET u otro método).

### `POST /api/pedidos-por-reasignar/aceptar/<id>/`

Body: `{"token": "ABC123"}`.

- `200` → `{"message": "Pedido aceptado", "pedido": {"id": 17, "estado": "asignado"}}`
- `409` → `{"message": "El pedido ya fue tomado por otro repartidor."}`
- `404` → no existe ese pedido · `403` / `404` → problemas con el token.

No se lee el paquete antes de escribir: el `UPDATE` condicional es la barrera
de concurrencia. En PostgreSQL la segunda transacción espera y reevalúa el
`WHERE` ya cambiado; en SQLite (tests) los escritos se serializan. No hace
falta `select_for_update` ni un bloqueo explícito de la fila. La respuesta del
aceptar **no** incluye `ultimo_repartidor`: después de tomarlo, la FK apunta al
nuevo repartidor y ese dato ya no tendría sentido (el front refresca la lista).

## Efectos en otras HUs (a tener en cuenta)

- `actualizacionEstado/views.py` **bloquea** cambiar el estado de un paquete
  `cancelado`. El endpoint de aceptar es propio y no pasa por ahí, así que
  puede hacer `cancelado → asignado`.
- `asignarRepartidor/views.py` (panel del coordinador) rechaza asignar
  `cancelado`. Tampoco interfiere: la toma la hace el repartidor desde acá.
- `historialEnvios` cuenta los `cancelado` en el historial del repartidor que
  los tiene asignados. Al reasignar, el paquete pasa a `asignado` y deja de
  figurar en ese historial. Es la consecuencia de no guardar un snapshot del
  repartidor anterior; si más adelante hace falta conservarlo, ahí sí habría
  que agregar un campo.
- `paquetesEnCurso` excluye solo `entregado`, así que los `cancelado` siguen
  apareciendo en el panel del coordinador mientras nadie los tome.

## Tests

```bash
cd backend
DATABASE_MODE=sqlite python manage.py test pedidosPorReasignar
# o toda la suite
DATABASE_MODE=sqlite python manage.py test
```

Cubren los dos escenarios de la HU, el contrato de la lista, el nombre y
apellido del último repartidor (y el caso sin repartidor), token/estado
operativo, que se puede tomar con otros pedidos ya asignados, que el segundo
repartidor recibe 409, que un pedido no cancelado no se puede tomar y el
**flujo completo** cancelar → listar → tomar usando
`/api/cambiar-estado-pedido/`, que es exactamente lo que hacen los dos
componentes de React.

## Frontend

`frontend/src/pages/PedidosPorReasignar.tsx` consume la lista con `POST` +
token, muestra retiro/destino/tamaño y "Última persona que lo retiró", y ante
un `409` refresca la lista avisando que otro repartidor se adelantó.
