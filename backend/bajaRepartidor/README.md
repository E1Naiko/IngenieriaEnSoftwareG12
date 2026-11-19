# bajaRepartidor — baja lógica de repartidores (HU #38)

Módulo Django que expone la API para **dar de baja a un repartidor** sin borrar
la fila: se cambia `repartidor.estado` a `baja` y el registro queda para el
historial. Es el backend que consume el botón **Dar de baja** de
`frontend/src/pages/EditarRepartidor.tsx`.

> **Ubicación:** `backend/bajaRepartidor/`
> **Modelo de datos:** `core.models.Repartidor` (este módulo **no** define modelos propios)
> **Rutas montadas en:** `config/urls.py → api/` + `bajaRepartidor/urls.py`

---

## 1. Propósito

- Implementar los escenarios de la HU #38: confirmar la baja, aplicarla y que
  el repartidor dado de baja no pueda volver a entrar.
- La baja es **lógica**. No se borran paquetes ni el historial: los `Paquete`
  que tenía asignados conservan la FK (`on_delete=SET_NULL` solo actúa si se
  borrara la fila, cosa que acá no pasa).

---

## 2. Endpoints

| Método | Ruta | Para qué |
|---|---|---|
| `GET` | `/api/repartidores/<id>/detalle-baja/` | Datos que muestra el modal de confirmación. |
| `POST` / `PATCH` / `DELETE` | `/api/repartidores/<id>/baja/` | Aplica la baja. El front usa `POST`. |

Las dos rutas están montadas bajo `/api/` y **no** chocan con las de
`crudRepartidor` (`GET/PUT /api/repartidores/<id>/`), porque el sufijo
`detalle-baja/` y `baja/` las distingue. Ese fue un pedido explícito en la
revisión del PR #79.

### Contrato JSON

`GET detalle-baja/` → `200`

```json
{
  "repartidor": {
    "id": 7,
    "nombre": "Ana",
    "apellido": "Paz",
    "dni": 30111222,
    "telefono": "2215550000",
    "mail": "ana@correo.com",
    "tipo_vehiculo": "auto",
    "estado": "ACTIVO"
  }
}
```

`POST baja/` → `200`

```json
{
  "mensaje": "Repartidor dado de baja con éxito",
  "repartidor": { "id": 7, "estado": "baja", "...": "resto de los datos" }
}
```

La respuesta **no** incluye `token` en ningún caso.

### Códigos de error

| Código | Cuándo | Cuerpo |
|---|---|---|
| `400` | El repartidor ya estaba de baja | `{"error": "El repartidor ya fue dado de baja"}` |
| `401` | No hay sesión de coordinador | `{"error": "No autenticado"}` |
| `404` | El id no existe | `{"error": "Repartidor no encontrado"}` |
| `405` | Método no permitido en esa ruta | HTML de Django |

---

## 3. Autenticación y CSRF

Hay una sola persona con el rol de coordinador, así que **estar logueado
alcanza** (`request.user.is_authenticated`), igual que en `historialEnvios`.
Un `401` hace que el front muestre el error sin abrir el modal.

Las vistas son `@csrf_exempt`. **No es un descuido**: todas las acciones del
coordinador en este proyecto lo son (ver `crudComercios/README.md`, sección 9,
y el `PUT` de edición de la HU #39 en `crudRepartidor/views.py`). El motivo es
el despliegue: el front llama por rutas relativas y el pedido llega
proxificado (rewrite de Vercel → Render, proxy de Vite, túneles de desarrollo),
así que el `Origin` del navegador no coincide con el host que ve Django. La
verificación CSRF de Django compara el `Origin` con `request.get_host()` y
responde **403** aunque el token sea correcto, con lo cual la baja no se podría
hacer nunca desde el front desplegado.

La protección efectiva es `SESSION_COOKIE_SAMESITE="Lax"` (valor por defecto):
un `POST` disparado desde otro sitio no lleva la cookie `sessionid`, entonces
`request.user` es anónimo y la vista responde `401`.
`BajaRepartidorProxificadoTests` cubre justamente ese escenario (cliente con
`enforce_csrf_checks=True`, `Host` del backend y `Origin` del frontend).

Si en el futuro el front y la API se sirven desde el **mismo dominio**, el
camino es: quitar los `@csrf_exempt`, cargar el dominio en
`CSRF_TRUSTED_ORIGINS` (ver `config/settings.py`) y no hay que tocar el front:
`frontend/src/utils/csrf.ts` ya manda `X-CSRFToken` en el `POST` de la baja y
en el `PUT` de edición.

---

## 4. Efecto de la baja

- `estado` pasa a `baja`. Se compara sin mayúsculas ni espacios, así que una
  fila con `BAJA` también cuenta como dada de baja (idempotencia).
- Se usa `Repartidor.objects.filter(...).update(...)`: no dispara
  `Repartidor.save()`, por lo tanto **el token se conserva**. La baja es
  lógica y el token queda como rastro; el login lo rechaza por el estado.
- El repartidor baja deja de aparecer en `/api/repartidores/lista/`, no puede
  iniciar sesión (`loginRepartidor`), no puede recuperar el token (HU #29), no
  recibe paquetes nuevos (`repartidoresDisponibles`, `asignarRepartidor`) y no
  puede cambiar su disponibilidad (`disponibilidadRepartidor`).

---

## 5. Tests

```bash
cd backend
DATABASE_MODE=sqlite python manage.py test bajaRepartidor
```

Cubren los escenarios de la HU (detalle, baja exitosa, baja repetida, id
inexistente, método incorrecto, sin sesión), que la baja no toque otros
campos, el escenario proxificado del despliegue y que la cookie de sesión sea
la única puerta de entrada.

---

## 6. Uso desde el frontend

`frontend/src/pages/EditarRepartidor.tsx`:

1. El botón **Dar de baja** llama a `pedirConfirmacionBaja(item)`: abre el
   modal con los datos de la lista y pide `detalle-baja/`; si ese pedido falla
   (por ejemplo, el repartidor ya estaba de baja), el modal se cierra y el
   error se muestra sobre la lista.
2. **Sí, dar de baja** llama a `darDeBaja(id)` (`POST`), cierra el modal y
   recarga la lista.
