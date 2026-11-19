# Sprint Review — Estado de las HUs para la presentación del 20/11/2026

> **Cómo leer esto.** Verificado contra el código (base: `main` en `ecefa1c`) y
> **actualizado el 19/11/2026 con la revisión de HUs del equipo**, que cambió la
> regla de #23: ahora la historia pide *comprobar* el DNI del cliente, no solo
> adjuntarlo. Esa validación **se implementó en este mismo cambio** (backend +
> frontend + 19 tests nuevos) y se probó contra el servidor levantado.
>
> Estado actual: **260 tests del backend en verde** y build del frontend
> (`npm run build`) sin errores. Incluye el PR #79 (baja de repartidores)
> mergeado el mismo día. Cuando digo "falta", lo probé con requests
> reales contra el endpoint, no es una impresión.
>
> **Buenas noticias para mañana:** **las 9 HUs se pueden demostrar**, porque el
> PR #79 (baja de repartidores) se mergeó mientras preparábamos la demo. La sección "Chuleta para la
> demo" al final tiene el recorrido sugerido.

---

## 1. Resumen en una tabla

| HU | Historia | Estado en `main` | ¿Se puede demostrar mañana? |
|----|----------|------------------|------------------------------|
| #22 | Cambiar disponibilidad del repartidor | ✅ Completa, con tests | Sí, sin salvedades |
| #35 | Publicar pedido "por reasignar" | ⚠️ Parcial (solo la mecánica de publicación) | Sí, pero con cuidado: ver §3 |
| #36 | Ver y tomar pedidos "Por Reasignar" | ✅ Completa, con tests | Sí, con 2 reglas simplificadas (§4) |
| #41 | Buscador de paquetes en curso | ✅ Completa en frontend | Sí, y es de las más vistosas |
| #42 | Buscador de comercio | ✅ Completa en frontend | Sí, es la demo más corta |
| #29 | Recuperar token | ✅ Completa, con tests | Sí, pero no la muestres como "segura" (§7) |
| #23 | Validar entrega con DNI | ✅ **Implementada en este cambio** | Sí, es la novedad (§8) |
| #39 | Edición de repartidores | ✅ Completa, con tests | Sí |
| #38 | Baja de repartidores | ✅ **Mergeada** (PR #79) mientras se preparaba este cambio | Sí (§10) |

La lista tiene 9 HUs y el repo tiene trabajo de sprint en **7 apps**. Con el
merge del PR #79 ya no queda ninguna HU de la lista fuera de `main`; las
salvedades que quedan son de alcance (qué reglas se simplificaron) y están
detalladas en cada sección.

---

## 2. #22 — Cambiar estado de disponibilidad ✅

**Qué hay.** `POST /api/disponibilidad-repartidor/` con `{"token": "...", "estado":
"disponible" | "no_disponible"}` y un `GET` con el token en la query. La pantalla
es la tarjeta **"Mi disponibilidad"** de `Dashboardrepartidor.tsx`, con modal de
confirmación y mensaje de éxito/error.

**Cumple las 3 reglas:**

- El token se valida en cada request (no hay sesión). Token inválido → `404`.
- `no disponible` guarda `estado='inactivo'`, y **la asignación del coordinador ya
  respeta eso**: `asignarRepartidor` filtra `ACTIVO`/`DISPONIBLE` y devuelve `400
  "El repartidor no está disponible."` si se fuerza. También desaparece de "Flota
  disponible" (`repartidoresDisponibles`).
- Un repartidor en `baja` recibe `403` y no puede cambiar su estado.

**Tests:** 17 en `backend/disponibilidadRepartidor/tests.py`, incluidos "pasa a
disponible", "pasa a no disponible", "dado de baja no puede cambiar" y el GET.

**Ojo con la terminología** si preguntan: la HU habla de "Disponible / No
disponible", el modelo guarda `ACTIVO / inactivo` y la base de dev tiene además
valores legados `DISPONIBLE`. La app normaliza los tres; el front solo ve
`disponible: true/false`. Esa es la respuesta correcta si alguien mira la base y
ve nombres distintos.

---

## 3. #35 — Publicar el pedido "por reasignar" ⚠️

Esta es la HU con más distancia entre lo que dice el enunciado y lo que hay en
`main`, así que preparala bien.

**Qué funciona hoy.** El repartidor toca "Confirmar cancelación", escribe un
motivo y el paquete pasa a `cancelado`. Como el endpoint **no limpia
`paquete.repartidor`**, ese paquete aparece automáticamente en la lista de "Por
Reasignar" (HU #36) y el coordinador lo ve en "Paquetes en curso". Hay un test de
flujo completo `cancelar → listar → tomar` que pasa.

**Qué NO cumple, verificado con requests reales:**

1. **Se publica con cualquier motivo**, no solo fuerza mayor. Probé cancelar con
   `"motivo": "accidente"`, con motivo vacío y con `"el cliente rechazó el
   pedido"`: en los tres casos el paquete quedó `cancelado` y publicado. La regla
   "no se activa cuando el cliente rechaza o no está en el domicilio" **no está**.
2. **El motivo no se guarda en ningún lado.** El front lo manda, el backend lo
   ignora: no hay columna `motivo_cancelacion` en el modelo (en `historialEnvios`
   hay una línea comentada que lo insinúa).
3. **No hay estado "Pendiente de reasignación"** ni "liberar del repartidor
   original": el paquete queda `cancelado` y con la FK al repartidor anterior (de
   ahí sale el "último repartidor" de la lista). Está documentado como decisión
   consciente en `pedidosPorReasignar/README.md`.
4. **El escenario "nadie lo toma" no existe**: no hay tiempo límite ni cola manual
   para el coordinador. Es más: **el coordinador no puede asignar un cancelado**
   (`asignarRepartidor` devuelve `409 "El paquete ya no está en curso."`). Hoy la
   única salida es que otro repartidor lo tome.

**Sobre la rama de #35:** existe
`#35-Publicar-pedido-en-la-lista-de-pedidos-por-reasignar-del-coordinador` y ahí
sí hay una implementación completa (causas `fuerza_mayor` / `cliente_ausente` /
`cliente_rechaza`, estado `pendiente_reasignacion`, `en_devolucion`,
`cancelado_por_cliente`, radio de 5 km, plazo de 15 min, cola manual). Los 201
tests de esa rama también pasan. **Pero esa rama no está mergeada ni tiene PR
abierto**, y agrega 3 migraciones (`0011`, `0012`, `0013`) que no están en `main`.
O sea: mañana en la demo el código que corre es el de `main`. Si te preguntan
"¿y lo de fuerza mayor?", la respuesta honesta es "está desarrollado en la rama,
falta integrarlo"; no lo presentes como terminado.

**Cómo mostrarla igual.** Enfocate en la mecánica que sí funciona: cancelar un
pedido en curso como repartidor y que aparezca solo en la lista del otro
repartidor, sin intervención del coordinador. Eso es el corazón de la historia.

---

## 4. #36 — Ver y tomar pedidos "Por Reasignar" ✅

**Qué hay.** Pantalla propia (`/dashboardrepartidor/reasignar`) con botón desde el
dashboard del repartidor. `POST /api/pedidos-por-reasignar/` lista y
`POST /api/pedidos-por-reasignar/aceptar/<id>/` toma.

**Lo mejor de esta HU para la demo:** la **concurrencia**. El aceptar es un
`UPDATE` condicional dentro de una transacción (`WHERE estado='cancelado'`), así
que si dos repartidores aceptan el mismo pedido, el segundo recibe `409` y el
front refresca la lista con el aviso "otro repartidor se adelantó". Hay tests de
"el primero que lo toma se lo queda" y hasta un test de flujo completo. Es un
buen punto para lucirse: es el tipo de detalle que un profesor valora.

**Reglas que cumplen:** token + estado operativo (`403` si inactivo/baja), se
puede tomar aunque ya tenga otros pedidos, cada pedido muestra solo
retiro/destino/tamaño (+ último repartidor), y al tomarlo aparece en "Mis pedidos".

**Reglas simplificadas (decirlas si preguntan, no esconderlas):**

- **No hay filtro por zona cercana**: entran todos los cancelados. De hecho el
  modelo `Repartidor` no tiene ni zona ni coordenadas (verifiqué los campos).
- **No se valida el tamaño del vehículo** al tomar un pedido por reasignar (sí se
  valida en la asignación manual del coordinador). Con la moto se puede tomar un
  paquete grande.
- El estado que la HU llama "Operativo" se mapea a `ACTIVO`; el modelo no tiene un
  `OPERATIVO` propio.

**Tests:** 18 en `backend/pedidosPorReasignar/tests.py`.

**Detalle para la demo:** la lista se arma con los paquetes `cancelado`, así que
para mostrarla tienen que cancelar uno primero (encadena bien con #35).

---

## 5. #41 — Buscador de paquetes en curso ✅

**Qué hay.** Input arriba de la tabla en la sección "Paquetes en curso" del
dashboard del coordinador. Filtra **en el cliente, mientras se escribe**, sobre
ID, destinatario, dirección, tamaño, repartidor y estado, normalizando tildes y
mayúsculas (`NFD` + quitar diacríticos + `toLowerCase`).

**Escenarios:**

- Con resultados: escribir "perez" encuentra "Pérez" ✅.
- Por repartidor o estado: escribe "juan" o "en camino" y filtra ✅ (busca tanto el
  valor `en_camino` como la etiqueta "En camino").
- Sin resultados: muestra `No se encontraron paquetes para "…"` con las comillas
  tipográficas ✅.
- **Combinado con el filtro "sin asignar"**: el filtro existe, se togglea, y la
  búsqueda se aplica **después** del filtro (el código es explícito:
  `(!soloSinAsignar || estaSinAsignar(p)) && coincideConBusqueda(...)`), así que el
  escenario 4 cumple ✅.

**Salvedad técnica:** el backend NO tiene parámetro de búsqueda; el endpoint
`/api/dashboard/paquetes-en-curso/` devuelve los 6 campos del contrato y el filtro
es 100% de frontend. Para el volumen de este TP está perfecto, y está documentado
así en `backend/README.md`. Si preguntan "¿por qué no en SQL?", la respuesta es
"el listado completo ya viaja al panel; filtrar en el cliente evita una request por
tecla y mantiene el mismo contrato". No lo vendas como indexado/DB.

---

## 6. #42 — Buscador de comercio ✅

**Qué hay.** Dos lugares, como pide la HU:

1. **Listado de comercios del dashboard**: input que filtra por nombre, dirección
   y teléfono (además del ID), con el contador **"Mostrando X de Y"** y el mensaje
   `No se encontraron comercios para "…"` ✅.
2. **Al elegir comercio al ingresar un pedido**: el popup de selección tiene su
   propio buscador con el mismo criterio, y al dar de alta un comercio **se limpia
   la búsqueda** para que el nuevo aparezca al volver ✅ (está comentado en el
   código: "limpia la búsqueda para que el elemento nuevo no quede oculto").

Los 4 escenarios se pueden demostrar tal cual están escritos.

**Salvedades:**

- El filtrado en esos dos lugares es de frontend. El backend acepta `?q=` pero
  **solo filtra por nombre** (`nombre__icontains`), no por dirección ni teléfono.
  Si alguien prueba la API directo con `?q=221-555` va a ver que devuelve todo.
  Que no te sorprenda: el front no usa ese parámetro.
- **`EditarComercio.tsx` no tiene buscador.** Si en la presentación alguien
  esperaba "buscador en el listado de comercios" y abre *Administrar comercios*,
  no lo va a encontrar; el buscador está en el listado del dashboard. Conviene
  aclarar en qué pantalla está antes de abrirla.

---

## 7. #29 — Recuperar token ✅ (con una salvedad de seguridad)

**Qué hay.** En el login del repartidor está el link **"Recuperar token"**. Pide
el DNI y:

- DNI registrado → genera un token nuevo de 6 caracteres y **lo muestra en
  pantalla** ✅ (el enunciado pide exactamente eso).
- DNI no registrado → `Datos incorrectos` ✅.
- El token viejo deja de servir (se reemplaza) y un repartidor de baja no puede
  recuperar (`403`).

**La salvedad:** el token se genera con `secrets.choice` sobre A-Z y 0-9 — eso
está bien —, pero **el DNI solo no es un factor de autenticación**. Cualquiera que
sepa o adivine un DNI puede regenerar el token de ese repartidor y quedarse con su
acceso, porque **no se pide nada más** (ni teléfono, ni mail, ni confirmación).
Además, al regenerarlo, si el repartidor real tenía sesión abierta se le
invalida. La HU lo pide así ("se identifica con su DNI"), así que está
implementado tal cual, pero si un profesor de seguridad pregunta, la respuesta es:
"la HU define el DNI como identificación; para producción habría que sumar un
segundo factor o enviarlo por un canal verificado". No lo presentes como
"recuperación segura".

**Detalle de implementación:** hay un `@staticmethod _generar_token()` en el
modelo que se usa tanto en el alta como en la recuperación, y valida unicidad
contra la base antes de devolverlo. Bien.

**Tests:** 7 en `backend/loginRepartidor/tests.py` (3 de login + 4 de
recuperación).

---

## 8. #23 — Validar entrega con comprobante de DNI ✅ (implementada hoy)

**Atención: la historia cambió.** Antes decía *"se necesita insertar el DNI del
cliente"*; ahora dice **"se necesita comprobar el DNI del cliente para marcar el
pedido como Entregado"**. Es decir: ya no alcanza con que el repartidor escriba
un número cualquiera, el sistema tiene que **verificar que sea el correcto**. Eso
es lo que se implementó y lo que conviene contar como novedad del sprint.

### Cómo funciona

1. El repartidor, en "Marcar como Entregado", ve un campo **"DNI del receptor"**
   (y, debajo, la foto del DNI como **opcional**).
2. El front manda `dni_receptor` junto con el estado.
3. El backend lo compara contra `paquete.cliente.dni`:
   - coincide → el paquete pasa a `entregado` (`200`), con mensaje
     *"Entrega validada con el DNI del receptor."*;
   - **falta** → `400` con el texto exacto de la HU:
     *"Necesario el numero del DNI del cliente para finalizar la entrega"*;
   - **no coincide** → `400` con *"El DNI ingresado no coincide con el del
     cliente del pedido. El DNI del cliente es …"*.
4. En los dos rechazos **el paquete no cambia de estado**: sigue `en_camino`.

### Decisiones que conviene saber si preguntan

- **Se muestra el DNI esperado cuando no coincide.** Es a propósito: el
  repartidor está en la puerta con el documento en la mano y tiene que poder
  corregir en el momento, no quedarse sin poder entregar. Es el mismo criterio
  que ya usan los mensajes de "dato repetido" del resto del sistema.
- **La foto es opcional**, no la regla. Antes el front *exigía* una foto que el
  backend **descartaba en silencio** (esa era la falla anterior). Ahora, si llega
  la foto, se guarda como `Comprobante` asociado al paquete; si no llega, el
  paquete queda igual que antes (`comprobante = NULL`). Así la historia se
  cumple completa y además se aprovecha el modelo de comprobantes que ya existía.
- **Se toleran formatos**: `30111222`, `"30.111.222"` o `" 30 111 222 "` se
  normalizan a dígitos antes de comparar. También acepta el campo `dni` además de
  `dni_receptor`.
- **Solo aplica al estado `entregado`**: los demás cambios de estado (en camino,
  cancelado) no piden DNI.

### Verificado de punta a punta (servidor real, no solo tests)

Con `preparar_demo` y `runserver`:

| Caso | Resultado |
|---|---|
| `entregado` sin `dni_receptor` | `400` con el texto de la HU, paquete sigue `en_camino` |
| `dni_receptor: "11111111"` (ajeno) | `400` "no coincide… es 33444555", paquete sigue `en_camino` |
| `dni_receptor: "33.444.555"` (correcto, con puntos) | `200`, pasa a `entregado` |
| `dni_receptor` correcto + `foto_dni` data URL | `200`, se crea `Comprobante` y el archivo queda en `media/comprobantes/2026/11/` |
| `foto_dni` mal formada | `400` "La foto del DNI no es válida" (antes se descartaba en silencio) |

### Tests

19 nuevos en `backend/actualizacionEstado/tests.py` (clase
`ValidarEntregaConDNITests`): DNI correcto, con puntos, campo alternativo,
sin DNI, DNI vacío/nulo/bool, DNI de otro cliente, que los otros estados no lo
pidan, foto opcional, foto guardada, foto mal formada y formato no admitido.

> El test que antes daba por buena una entrega **sin DNI** se reescribió: era
> justamente el comportamiento que la historia actual prohíbe.

### Paso a producción

No hace falta migración: se usa `Comprobante`, que ya existía. Solo hay que
aplicar `python manage.py migrate` si había migraciones pendientes y asegurarse
de que `/media/` esté servido en el entorno (en desarrollo lo hace Django; en
producción lo resuelve el servidor web o un storage, como ya dice el README).

## 9. #39 — Edición de repartidores ✅

**Qué hay.** En *Administrar repartidores* (`/repartidores`) el coordinador elige
uno de la lista y edita nombre, apellido, DNI, celular, email y tipo de vehículo.
`GET`/`PUT /api/repartidores/<id>/`.

**Reglas:**

- El **token se muestra pero es `readOnly`** en el formulario y el `PUT` **no lo
  toca** (solo actualiza los 6 campos editables). `estado` tampoco se pisa ✅.
- **DNI, email y teléfono únicos**: la validación compara contra todos los otros
  repartidores (`excluir_pk`) y devuelve `{"campo": "Este dato ya existe en el
  sistema"}`. El email y el teléfono se comparan con `__iexact` (o sea, "Ana@X.com"
  choca con "ana@x.com") ✅.
- Mensaje **"Repartidor modificado con éxito"** en el modal de confirmación ✅.
- **Activos e inactivos**: la lista excluye solo `baja`, así que salen ambos ✅.
- Detalle: nombre y apellido se normalizan a "Primera Mayúscula" al guardar, y el
  mail se guarda en minúsculas. Si lo comparás con el alta, es coherente.

**Tests:** 18 en `backend/crudRepartidor/tests.py` (alta, edición, repetidos,
validaciones, lista).

**Chuleta:** el botón de la pantalla dice "Editar repartidor" y luego "Guardar
cambios", tal cual el escenario de la HU. Para mostrar "este dato ya existe",
editá un repartidor y poné el DNI de otro de la lista.

---

## 10. #38 — Baja de repartidores ✅ (mergeada el 19/11, PR #79)

**Ya está en `main`.** El PR #79 se mergeó mientras se preparaba este documento,
así que la baja se puede demostrar completa.

**Qué hay:**

- Botón **"Dar de baja repartidor"** en *Administrar repartidores*, con modal que
  muestra los datos y el texto *"¿Seguro que desea dar de baja al repartidor?"*,
  y los botones **"Sí, dar de baja"** / cancelar.
- `GET /api/repartidores/<id>/detalle-baja/` (datos del modal) y
  `POST /api/repartidores/<id>/baja/`, ambos con **sesión de coordinador**
  (`401` si no hay).
- La baja es **lógica**: `estado='baja'`, no se borra la fila, no se toca el
  token y no se pierden los paquetes ni el historial.
- **El token no se puede volver a usar**: el login lo rechaza (*"El repartidor no
  se encuentra habilitado…"*), la recuperación de token (#29) también, y no
  aparece en la lista de edición ni en la flota disponible.
- `backend/core/estados.py` centraliza la comparación de `baja`, así que
  `BAJA` en mayúsculas también cuenta como baja (era un bug real: el login
  comparaba contra el literal `"baja"`).

**Efecto colateral que hay que tener presente en la demo:** el PR #79 también
endureció el endpoint de cambio de estado. Ahora `POST /api/cambiar-estado-pedido/`
**exige el token del repartidor** (`400` sin token, `401` si no existe, `403` si
está de baja) y **rechaza cambiar paquetes que no son suyos** (`403`). El
frontend ya mandaba el token, así que las pantallas funcionan igual, pero si
alguien prueba la API con `curl` sin token va a recibir `400`. Es una mejora, no
una regresión.

**Cómo demostrarla:** dar de baja a un repartidor, mostrar el modal, cancelar (el
modal desaparece y no pasa nada), volver a abrirlo y confirmar. Después intentar
iniciar sesión con el token de ese repartidor: el sistema lo rechaza.

## 11. Cosas que encontré de paso y conviene tener a mano

No son parte de las HUs, pero pueden aparecer si alguien navega:

- **Alta de repartidor (#25)**: existe el endpoint y el componente
  `AltaRepartidor.tsx`, pero **no hay ruta ni botón en el menú** (`App.tsx`) para
  llegar a la pantalla desde la UI. Es un detalle de navegación, no de backend.
- **La entrega ya está cerrada en el backend**: desde el cambio de #23 no se
  puede marcar `entregado` por API sin el DNI correcto del cliente (antes sí).
  Es un buen argumento para mostrar si alguien pregunta por validaciones.
- **El coordinador no está autenticado en la mayoría de los endpoints**: solo
  `historialEnvios` y la baja (#38) exigen sesión. `loginCoordinador` crea la cookie, pero
  `crudRepartidor`, `crudComercios`, `asignarRepartidor`, `paquetesEnCurso`,
  `pedidosPorReasignar`, etc. son `@csrf_exempt` y abiertos. Es una decisión de
  alcance del TP; si preguntan, "la autenticación del coordinador está resuelta en
  el login y falta aplicarla a todos los endpoints del panel". No la vendas como
  seguridad completa.
- **HU41 y HU42 son las más sólidas para arrancar la demo**: son visuales, se
  entienden en 10 segundos y no dependen de datos raros. Dejalas temprano.
- **Tests**: `DATABASE_MODE=sqlite python manage.py test` → **214 OK** en ~8 s.
  Ese comando es una buena respuesta si preguntan "¿cómo prueban?".

---

## 12. Chuleta para la demo (recorrido sugerido)

1. **Coordinador → Dashboard** (login de coordinador).
2. **#41**: en "Paquetes en curso", escribir un apellido con tilde ("pérez") y
   después "en camino"; mostrar "No se encontraron paquetes para "…"" con algo
   que no exista; prender **Sin asignar** y buscar una dirección. 3 minutos.
3. **#42**: en "Comercios", buscar por teléfono y por dirección; mostrar
   "Mostrando X de Y". Después abrir *Nuevo pedido* y usar el buscador en el popup
   de comercio. 2 minutos.
4. **#22**: entrar como repartidor, mostrar "Disponible", pasar a "No disponible"
   (modal + mensaje). Volver al coordinador y mostrar que **ya no aparece** en
   "Flota disponible". Ese ida y vuelta es el que mejor cuenta la historia.
   3 minutos.
5. **#36 + #35**: como repartidor A, cancelar un pedido en curso con motivo. Como
   repartidor B, abrir **"Pedidos por Reasignar"**: el pedido está ahí con
   retiro/destino/tamaño. Aceptarlo y mostrar que desaparece de la lista y aparece
   en "Mis pedidos". Si querés el momento "wow": abrí las dos sesiones de
   repartidor y que B y C acepten a la vez; el segundo ve el aviso del `409`.
   4 minutos.
6. **#39**: *Administrar repartidores* → Editar → cambiar el celular → "Guardar
   cambios" → "Repartidor modificado con éxito". Después intentar poner el DNI de
   otro → "Este dato ya existe en el sistema". Mostrar que el Token está en gris.
   2 minutos.
7. **#29**: cerrar sesión de repartidor → "Recuperar token" → DNI registrado →
   aparece el token nuevo → entrar con él. Probar un DNI inexistente → "Datos
   incorrectos". 2 minutos.
8. **#38**: dar de baja a un repartidor mostrando el modal, cancelar y volver a
   confirmar; después intentar entrar con su token y ver el rechazo. 2 minutos.
9. **#23**: si querés cerrar con la novedad del sprint, entregar un pedido
   **sin** el DNI (mensaje exacto de la HU), con un DNI equivocado (el sistema
   dice cuál es el correcto) y con el correcto. 2 minutos y es la mejor
   respuesta a "¿qué validan al entregar?".

**Orden alternativo si falta tiempo:** 41 → 42 → 22 → 36 (con el 409) → 23 → 29.
Es el 80% del valor de la demo en 13 minutos y todo lo que se muestra funciona.

---

## 13. Preguntas probables y respuestas cortas

- **"¿Cuántos tests tienen?"** 260 en el backend, 16 apps cubiertas, corren en
  ~13 segundos con SQLite; el CI también construye la imagen Docker y consulta
  `/api/ping/`.
- **"¿Por qué la búsqueda no está en la base?"** Porque el listado completo ya se
  sirve al panel y el filtro en el cliente evita una request por tecla; para el
  volumen del TP es de sobra, y el contrato de la API no cambia.
- **"¿Qué pasa si dos repartidores toman el mismo pedido?"** `UPDATE` condicional
  atómico: el segundo actualiza 0 filas y recibe `409`. Hay test y se puede
  mostrar en vivo.
- **"¿La baja borra datos?"** Es lógica: `estado='baja'`, no se borra la fila, no
  se toca el token ni se pierden sus paquetes o su historial, y el repartidor
  deja de poder entrar. Ya está en `main`.
- **"¿Y el DNI del receptor?"** Se valida contra el DNI del cliente del pedido:
  si falta, el sistema responde con el texto de la HU y el paquete no se marca
  entregado; si no coincide, indica el correcto. La foto es opcional y se guarda
  como comprobante (HU #23, implementada).
- **"¿Por qué hay estados en mayúsculas en la base?"** Hay datos de DEV con
  `ACTIVO`/`DISPONIBLE`/`ENTREGADO` de distintas épocas; el código compara
  siempre normalizado (`iexact`, `Lower(Trim(...))`) y hay una migración (`0009`)
  que unificó `ACTIVO`. Es una respuesta que muestra criterio, conviene tenerla.
