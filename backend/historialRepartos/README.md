# historialRepartos — Historial de repartos (HU: ver el historial)

Endpoints para que el **coordinador** consulte el historial de pedidos
entregados. Hay un historial **por cada repartidor**: el coordinador entra al
historial, elige un repartidor y ve su historial completo.

> **Ubicación:** `backend/historialRepartos/`
> **Modelo de datos:** no crea tablas. Lee `core.models.Repartidor` y
> `core.models.Paquete` (relación inversa `paquete.repartidor`), así que no
> tiene modelos ni migraciones propias.
> **Rutas:** `GET /api/historial/` y `GET /api/historial/<id>/` (montadas en
> `config/urls.py → api/`).

---

## 1. Reglas de la HU

| Regla | Cómo se resuelve |
|---|---|
| Solo el Coordinador puede ver el historial | Los dos endpoints exigen sesión de coordinador (`request.user.is_authenticated`). Sin sesión → `401` con `{"message": "Solo el coordinador puede ver el historial."}`. |
| Hay un historial por cada repartidor | El escenario 2 filtra siempre por `paquete.repartidor = <id>`: nunca devuelve pedidos de otro repartidor. |

¿Por qué la sesión alcanza? El **coordinador** es el único rol con cuenta de
Django (`loginCoordinador`, HU #4, que deja la cookie `sessionid`). El
**repartidor** entra con su token (`loginRepartidor`, HU #9) y no inicia
sesión, así que no puede llegar a estos endpoints. Si en el futuro se agregan
roles con usuario de Django, el único cambio va en `_es_coordinador()`.

**Qué es una entrega.** El historial son los paquetes con estado `entregado`
(misma definición que la property `Repartidor.historial_asociado` del modelo).
`pendiente`, `retirado`, `en_camino` y `cancelado` todavía no forman parte del
historial. La comparación ignora mayúsculas porque el estado es un `varchar`
libre y la base de desarrollo guarda algunos valores en mayúscula.

---

## 2. Contrato de la API

### Escenario 1 — el coordinador presiona "historial"

```
GET /api/historial/
```

Es el selector de repartidores de la pantalla. Devuelve a **todos** los
repartidores (también `inactivo` y `baja`: el historial no se borra cuando
alguien deja la flota), ordenados por apellido y nombre, con el resumen de su
historial.

```json
{
  "repartidores": [
    {
      "id": 3,
      "nombre": "Juan",
      "apellido": "Gómez",
      "dni": 40111222,
      "telefono": "221-555-0300",
      "mail": "juan@example.com",
      "tipo_vehiculo": "moto",
      "estado": "activo",
      "entregas": 12,
      "ultima_entrega": "2026-10-27"
    }
  ],
  "total_repartidores": 1
}
```

- `entregas` cuenta solo paquetes `entregado`; un repartidor nuevo aparece con
  `0` (no desaparece de la lista).
- `ultima_entrega` es la `fecha_destino` más reciente, o `null` si no tiene
  entregas.
- Sin repartidores: `200` con `{"mensaje": "No hay repartidores registrados...",
  "repartidores": [], "total_repartidores": 0}`.
- Las dos agregaciones (`Count` y `Max`) van anotadas en el mismo queryset, así
  que la lista se resuelve en **una** consulta.

### Escenario 2 — el coordinador selecciona un repartidor

```
GET /api/historial/<id>/
```

```json
{
  "repartidor": {
    "id": 3,
    "nombre": "Juan",
    "apellido": "Gómez",
    "dni": 40111222,
    "telefono": "221-555-0300",
    "mail": "juan@example.com",
    "tipo_vehiculo": "moto",
    "estado": "activo"
  },
  "entregas": [
    {
      "id": 7,
      "cod_seguimiento": "SRFR-1A2B3C4D",
      "estado": "entregado",
      "tamanio": "chico",
      "comercio": "Kiosco Central",
      "destinatario": "Ana Pérez",
      "direccion": "Calle 12 #34",
      "fecha_origen": "2026-10-20",
      "fecha_destino": "2026-10-27",
      "comprobante": "/media/comprobantes/2026/10/foto.jpg"
    }
  ],
  "total_entregas": 1
}
```

- Orden: del más reciente al más viejo (`fecha_destino` DESC; a igualdad de
  fecha, el último cargado).
- `estado` sale normalizado en minúsculas aunque la fila guarde `ENTREGADO`.
- `comprobante` es la URL del archivo que acredita la entrega, o `null` si
  todavía no se subió.
- Repartidor sin entregas: `200` con `"entregas": []`, `"total_entregas": 0` y
  un `"mensaje"` aclaratorio (no es un error: el historial existe, está vacío).
- `select_related("cliente", "comercio", "comprobante")` resuelve las tres FKs
  en el mismo JOIN: no hay una consulta por entrega.

### Códigos de respuesta

| Caso | Código | Respuesta |
|---|---|---|
| Listado o historial consultado con sesión de coordinador | `200` | JSON de arriba |
| Sin sesión de coordinador (incluye llamar la API directo) | `401` | `{"message": "Solo el coordinador puede ver el historial."}` |
| `<id>` de un repartidor que no existe | `404` | `{"detail": "Repartidor no encontrado."}` |
| Método distinto de `GET` | `405` | sin cuerpo |

El `401` se resuelve **antes** de buscar al repartidor: sin sesión no se puede
averiguar si un id existe.

---

## 3. Estructura

```
historialRepartos/
├── __init__.py
├── apps.py        # AppConfig
├── views.py       # historial_repartidores (escenario 1) y historial_repartidor (escenario 2)
├── urls.py        # historial/ y historial/<id>/
├── tests.py       # 23 tests: escenarios, reglas y bordes
└── README.md      # este archivo
```

Cambios fuera de la app: `"historialRepartos"` en `INSTALLED_APPS`
(`config/settings.py`) y `path("api/", include("historialRepartos.urls"))` en
`config/urls.py`. `config/tests.py` verifica ese cableado: si falta, los tests
fallan.

---

## 4. Probar

```bash
cd backend
DATABASE_MODE=sqlite python manage.py test historialRepartos
```

A mano, con `runserver` levantado y el coordinador ya creado
(`python manage.py createsuperuser`):

```bash
# 1. Iniciar sesión y guardar la cookie
curl -c cookies.txt -X POST http://127.0.0.1:8000/api/login-coordinador/ \
  -H "Content-Type: application/json" \
  -d '{"username":"coordinador","password":"TU_CLAVE"}'

# 2. Listado de repartidores con el resumen de su historial
curl -b cookies.txt http://127.0.0.1:8000/api/historial/

# 3. Historial completo de un repartidor (id del paso anterior)
curl -b cookies.txt http://127.0.0.1:8000/api/historial/3/

# Sin la cookie: 401
curl -i http://127.0.0.1:8000/api/historial/
```

---

## 5. Qué tiene que hacer el front

- El botón **"historial"** del menú abre la pantalla que llama a
  `GET /api/historial/` (ruta relativa: pasa por el proxy de Vite).
- Esa pantalla lista `repartidores` y, al elegir uno, llama a
  `GET /api/historial/<id>/`.
- Los `fetch` tienen que ir con `credentials: "same-origin"` (o mismo origen,
  que es el default) para que viaje la cookie de sesión; si no, la API
  responde `401`.
- Si la respuesta es `401`, conviene redirigir al login del coordinador.

Ejemplo:

```ts
const respuesta = await fetch("/api/historial/", { credentials: "same-origin" });
if (respuesta.status === 401) {
  // no hay sesión de coordinador: volver al login
}
const { repartidores } = await respuesta.json();
```
