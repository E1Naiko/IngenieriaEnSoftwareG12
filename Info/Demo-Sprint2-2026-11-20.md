# Demo Sprint 2 — viernes 20/11/2026

> **Lo que dijo la cátedra:** máximo **30 minutos**, frente al **cliente (Ariel o
> Rocío)**, con **todos los integrantes presentes**, y **10 minutos de
> retrospectiva** al terminar. Es una instancia de evaluación y empieza a la hora
> asignada en el archivo de horarios.
>
> Este documento es el guion. El estado técnico de cada HU está en
> [Estado-Sprint-2026-11-19.md](Estado-Sprint-2026-11-19.md).

---

## 0. La decisión más importante: qué NO mostrar

Con el cliente adelante y un reloj, conviene elegir **pocas cosas que funcionan
perfecto** antes que muchas a medias. Propuesta:

| ✅ Entra a la demo | ⛔ No entra |
|---|---|
| #23 **validar entrega con el DNI** ← la novedad | El **botón** "Dar de baja" (#38): está en el PR #79 |
| #41 buscador de paquetes (visual, 10 s) | Afirmar que #35 distingue fuerza mayor |
| #42 buscador de comercios | Detalles de seguridad del coordinador |
| #22 disponibilidad del repartidor | Recorridos por el admin de Django |
| #36 tomar pedidos por reasignar (+ el 409) | |
| #39 edición de repartidor (token en gris) | |
| #29 recuperar token | |

> **Cambio respecto de la versión anterior:** la historia #23 se actualizó
> (ahora pide *comprobar* el DNI, no solo adjuntarlo) y **se implementó**. Antes
> figuraba como "no mostrar"; ahora es la escena de cierre, porque es lo más
> nuevo del sprint y se defiende muy bien en vivo.

Si el cliente pide ver el botón de baja, la respuesta está en §6: reconocer el
alcance y mostrarlo como próximo paso. Es mucho mejor que descubrirlo en vivo.

---

## 1. Roles (7 personas, 7 responsabilidades)

Ajusten los nombres según quién desarrolló cada HU; lo que importa es que
**cada persona tenga un rol visible** y que nadie improvise el día de la demo.

| Rol | Qué hace | Quién |
|---|---|---|
| **Presentador/a** | Abre, presenta al equipo y cierra. Es la voz principal. | — |
| **Operador/a coordinador** | Maneja el panel del coordinador en las escenas 1 y 4. | — |
| **Operador/a repartidor A** | Sesión de repartidor en las escenas 2, 3 y 5. | — |
| **Operador/a repartidor B** | Segunda sesión de repartidor en la escena 3 (el 409). | — |
| **Datos y tokens** | Corre `preparar_demo`, tiene la tabla de tokens impresa y restaura si algo se rompe. | — |
| **Cronometrista** | Marca los tiempos de §3 y avisa con la mano a los 24 minutos. | — |
| **Narrador/a de cierre** | Cuenta qué se entregó, qué queda y los próximos pasos (§5). | — |

> El cronometrista no es un rol decorativo: con 30 minutos y cliente
> preguntando, es lo único que evita quedarse sin tiempo para el cierre.

---

## 2. Preparación (30 minutos antes)

### 2.1 Datos de demo (obligatorio)

Desde `backend/`, con el entorno virtual activado:

```bash
python manage.py revisar_db            # confirmar que es la base de DESARROLLO
python manage.py migrate               # por si falta alguna migración
python manage.py preparar_demo --confirmar-desarrollo
```

El comando:

- Crea 3 repartidores (2 activos + **1 dado de baja**), 3 comercios, 3 clientes
  y 7 paquetes con **códigos fijos** (`SRFR-DEMO0001`…): 2 cancelados para
  "Por Reasignar", 1 sin asignar, 1 entregado y el resto en curso.
- **Es idempotente y restaurador**: si se hizo un ensayo y los paquetes quedaron
  en otro estado, se vuelve a correr y queda igual que al principio.
- **Imprime los tokens** de los tres repartidores en pantalla. Copiarlos al
  papel/nota: son lo único que no se ve en una lista del sistema.

Verificado: 220 tests del backend pasan, incluidos 6 del comando
(`core.tests.PrepararDemoTests`).

### 2.2 El usuario del coordinador

```bash
python manage.py createsuperuser      # solo si no existe todavía
```

Anotar usuario y contraseña en el papel de la demo. No inventarlo a las 11:59.

### 2.3 Checklist de 8 puntos (15 minutos antes)

- [ ] Backend y frontend levantados; `/api/ping/` responde.
- [ ] Login del coordinador probado **una vez** (no en vivo por primera vez).
- [ ] `preparar_demo` corrido y tokens anotados en papel.
- [ ] Dos navegadores (o una ventana normal + una incógnita) para las dos
      sesiones de repartidor de la escena 3. Si usan incógnito, recordar que al
      cerrar se pierde el `localStorage`.
- [ ] Zoom del navegador al 110–125 %: el cliente tiene que leer las tablas.
- [ ] Notificaciones del sistema en "No molestar"; pestañas y chats cerrados.
- [ ] Un celular con **cronómetro** a la vista (el del cronometrista).
- [ ] Guion impreso para quien presenta y tabla de tokens para el operador.

### 2.4 Riesgo de latencia (ya lo tenían anotado en el Scrum)

La base de desarrollo está en USA-W: cada escritura puede tardar. Si la demo va
contra Supabase y la red del aula es lenta, **usar el plan local**:

```bash
# terminal 1
cd backend && DATABASE_MODE=sqlite python manage.py migrate
DATABASE_MODE=sqlite python manage.py preparar_demo --confirmar-desarrollo
DATABASE_MODE=sqlite python manage.py runserver

# terminal 2
cd frontend && npm run dev        # el proxy de Vite ya apunta a 127.0.0.1:8000
```

Los datos y los flujos son exactamente los mismos: SQLite es una base más del
mismo proyecto (el README la contempla como alternativa offline).

---

## 3. Guion minuto a minuto — Plan A (24 min de contenido + 6 de colchón)

| Min | Escena | Quién opera | Qué se ve en pantalla | Frase de arranque |
|---|---|---|---|---|
| 0–2 | Apertura | Presentador/a | Login del sistema | "Somos el grupo 12; en estos 30 minutos mostramos el circuito completo: coordinador, repartidor y reasignación." |
| 2–6 | **1. Buscadores (#41 y #42)** | Coordinador | Dashboard | "El coordinador recibe pedidos por WhatsApp; buscarlos tiene que ser instantáneo." |
| 6–9 | **2. Disponibilidad (#22)** | Repartidor A | Dashboard del repartidor | "El repartidor decide cuándo está disponible, y eso cambia lo que el coordinador puede asignarle." |
| 9–15 | **3. Reasignación (#36)** | Repartidor A + B | Dos sesiones | "Si a un repartidor le pasa algo, el pedido no vuelve al coordinador: vuelve a la flota." |
| 15–18 | **4. Edición (#39)** | Coordinador | Administrar repartidores | "Los datos del repartidor se editan sin tocar su token." |
| 18–21 | **5. Recuperar token (#29)** | Repartidor A | Login del repartidor | "Si el repartidor olvida el token, lo recupera solo, sin llamar a nadie." |
| 21–24 | **6. Entrega con DNI (#23)** | Repartidor B | Mis pedidos | "La entrega se cierra comprobando el DNI del cliente, no con un tilde." |
| 24–25 | **Cierre** | Narrador/a | — | "Esto es lo entregado, esto lo que sigue." |
| 25–30 | Preguntas | Todos | — | Colchón. |

### Escena 1 — Buscadores (4 min)

1. En "Paquetes en curso", escribir **`gomez`** (sin tilde): aparece el paquete
   de *Ana Gómez*. → "No importan mayúsculas ni tildes."
2. Borrar y escribir **`en camino`**: se filtra por estado con la etiqueta en
   castellano.
3. Escribir **`zzz`**: aparece *No se encontraron paquetes para "zzz"*. →
   "El sistema nunca deja la pantalla en blanco sin explicar por qué."
4. Prender el filtro **Sin asignar** y buscar una dirección: solo los paquetes
   sin repartidor que coinciden. → "Los filtros se combinan."
5. Bajar a "Comercios", buscar **`221-555-01`** (teléfono parcial) y después
   **`espiga`**. Mirar el contador **"Mostrando X de Y"**.
6. Abrir *Nuevo pedido* → elegir comercio: **el mismo buscador está en el popup**
   y al dar de alta un comercio se limpia solo. → "Buscamos donde el coordinador
   trabaja, no en una pantalla aparte."

### Escena 2 — Disponibilidad (3 min)

1. Repartidor A inicia sesión con su token: la tarjeta muestra **Disponible**.
2. Pasar a **No disponible** (modal de confirmación) → mensaje de éxito.
3. **Volver al coordinador** y mostrar "Flota disponible": ya no está. →
   "El estado no es un cartel: el coordinador ya no puede asignarle pedidos."
4. (Opcional, si hay tiempo) intentar asignarle uno y mostrar que el sistema lo
   rechaza. Esto es lo que más impresiona del ida y vuelta.

### Escena 3 — Reasignación (6 min) — la escena estrella

1. Repartidor A (Valentina) tiene un pedido `en_camino`. Tocar **Confirmar
   cancelación**, escribir el motivo ("se me pinchó la cubierta"), confirmar.
2. Repartidor B (Marcos, otro navegador) entra a **Pedidos por Reasignar**:
   el pedido está en la lista con **retiro, destino y tamaño** (lo justo para
   decidir). → "Nadie del equipo del coordinador intervino."
3. Marcos acepta: desaparece de la lista y aparece en **Mis pedidos**.
4. **El momento del 409** (si el tiempo lo permite): preparar dos sesiones de
   repartidor en la misma lista, que ambas acepten el mismo pedido casi a la
   vez; la segunda recibe el aviso "otro repartidor se adelantó" y la lista se
   refresca. → "El pedido no puede quedar en dos manos: el sistema lo impide."

> **Cómo presentar #35 sin sobrevender.** La publicación automática funciona
> (cancelar lo saca de un repartidor y lo pone en la lista del otro). Lo que
> **no** está en la versión integrada es la distinción por motivo (fuerza mayor
> vs. cliente ausente) ni la cola manual por tiempo vencido: eso está
> desarrollado en una rama, pendiente de integrar. Si preguntan, decirlo así.
> No hace falta que el cliente lo sepa de antemano, pero tampoco inventarlo.

### Escena 4 — Edición de repartidor (3 min)

1. Coordinador → *Administrar repartidores* → elegir uno → **Editar**.
2. Mostrar el **Token en gris** (solo lectura). → "El token no se puede cambiar
   desde acá: es la llave del repartidor."
3. Cambiar el celular → **Guardar cambios** → *"Repartidor modificado con
   éxito"*.
4. Intentar poner el **DNI de otro** repartidor → *"Este dato ya existe en el
   sistema"*. → "DNI, mail y teléfono son únicos: no hay dos repartidores
   duplicados."

### Escena 5 — Recuperar token (3 min)

1. Cerrar sesión del repartidor → **Recuperar token** → DNI de Valentina →
   aparece el token nuevo. Entrar con él.
2. Probar un DNI inventado → *"Datos incorrectos"*.
3. Aclaración honesta si preguntan: "hoy la identificación es el DNI, como pide
   la historia; para producción sumaríamos un segundo factor".

### Escena 6 — Entrega con DNI (3 min) — la novedad del sprint

Usar el pedido de **Marcos** (`SRFR-DEMO0002`, destinataria *Julián Fernández*,
DNI `35666777`). Si ya se tomó el pedido en la escena 3 y quedó `asignado`,
primero "Marcar como En camino".

1. **Marcar como Entregado** → aparece el campo **DNI del receptor** (y la foto,
   marcada como *opcional*).
2. Confirmar **sin escribir nada** → mensaje exacto de la historia:
   *"Necesario el numero del DNI del cliente para finalizar la entrega"*.
   El pedido **sigue en camino**. → "No se puede cerrar una entrega sin el
   documento."
3. Escribir un DNI equivocado (`11111111`) → *"El DNI ingresado no coincide con
   el del cliente del pedido. El DNI del cliente es 35666777."* → "El sistema no
   solo rechaza: le dice al repartidor cuál es el DNI correcto, porque está en
   la puerta del cliente."
4. Escribir el correcto (`35.666.777`, con puntos) → *"Entrega validada con el
   DNI del receptor."* y el pedido pasa a **Entregado**.
5. (Opcional, 20 s) Adjuntar una foto antes de confirmar: se guarda como
   comprobante de la entrega.

> **Por qué esta escena cierra la demo:** es la única HU que cambió de regla
> respecto de la versión anterior de la historia ("insertar" → "comprobar"), y
> demuestra que el sistema *valida*, no solo *registra*. Los tres casos
> (falta / no coincide / coincide) se muestran en menos de dos minutos.

---

## 4. Plan B — si algo falla (6 min, una sola persona)

No se cancela la demo: se reduce. Con un navegador y el coordinador ya logueado:

1. Buscar `gomez` y `en camino` (#41) — 1 min.
2. Buscar `espiga` y mostrar "Mostrando X de Y" (#42) — 1 min.
3. Mostrar la lista de "Por Reasignar" con el token de Marcos (#36) — 1 min.
4. Editar un repartidor, mostrar el token en gris y el dato repetido (#39) —
   2 min.
5. Entregar un pedido sin DNI y con DNI incorrecto (#23) — 1 min.
6. Cierre con el estado por HU de `Info/Estado-Sprint-2026-11-19.md` — 1 min.

**Plan C** (sin red o sin servidores): capturas de pantalla en una carpeta del
escritorio, numeradas en el orden del guion. Se consiguen en el ensayo del
jueves. Nunca se muestran archivos sueltos del repo ni la base en el admin.

---

## 5. Cierre (3 min): qué se dice

- **Entregado en el sprint:** validación de la entrega con el **DNI del
  receptor** (#23), buscadores (#41, #42), disponibilidad (#22), reasignación
  (#36, con bloqueo concurrente), edición de repartidor (#39), recuperación de
  token (#29), más el circuito de pedidos, asignación por vehículo y
  disponibilidad, historial y estado del envío de sprints anteriores.
- **En revisión:** baja de repartidor (#38) completa y con tests, esperando
  aprobación del PR.
- **Próximo paso:** integración de las causas de cancelación de #35 (fuerza
  mayor vs. cliente ausente) y la cola de reasignación manual.
- **Calidad:** 232 tests automáticos en el backend, integración continua que
  corre tests y build de la imagen en cada PR.

Es mejor decir "esto falta" que dejar que el cliente lo descubra: el cliente
valora un roadmap honesto más que una demo perfecta de dos minutos.

---

## 6. Preguntas probables del cliente (y respuesta corta)

| Pregunta | Respuesta |
|---|---|
| "¿Cómo se aseguran de que entregó a la persona correcta?" | "El repartidor carga el DNI del receptor y el sistema lo compara con el del cliente: si falta, no lo deja cerrar la entrega; si no coincide, le indica cuál es el correcto. La foto del DNI es opcional y queda como comprobante." |
| "¿Y si nadie toma el pedido reasignado?" | "Hoy queda en la lista hasta que alguien lo toma. La cola para que el coordinador lo asigne a mano está desarrollada en una rama y entra en la próxima integración." |
| "¿Cómo doy de baja a un repartidor?" | "La baja está implementada y probada en una rama, en revisión; hoy un repartidor dado de baja ya no puede ingresar al sistema." |
| "¿Y si el repartidor se equivoca de estado?" | "Puede cambiarlo cuando quiera, con confirmación; y el coordinador ve el cambio en la flota al instante." |
| "¿Dos repartidores pueden tomar el mismo pedido?" | "No: el segundo recibe un aviso y la lista se refresca. Está cubierto con tests." |
| "¿Se puede buscar por teléfono del comercio?" | "Sí, en el listado y al cargar un pedido: nombre, dirección o teléfono, sin importar tildes ni mayúsculas." |
| "¿Esto es seguro? ¿Quién entra?" | "El coordinador tiene usuario y contraseña; el repartidor, token único. La aplicación de permisos a todos los endpoints del panel está en el backlog técnico." |

---

## 7. Retrospectiva (10 min, después de la demo)

Formato sugerido: 2 min de hechos, 3 de "qué mejorar", 5 de acciones con
responsable. Ítems que ya están sobre la mesa (salieron del repo, no hace falta
inventarlos):

**Funcionó**
- La integración por PR con CI verde en cada uno: detectó errores antes del
  merge.
- Los READMEs por app: quien tomó una HU después entendió el contrato sin
  preguntar.
- El patrón de "token en cada request, sin sesión" para el repartidor: simple y
  consistente en todas las apps.

**Mejorar**
- **Integración a último momento:** la rama de #35 quedó completa sin PR abierto
  y la de #38 sin mergear a horas de la demo. Propuesta: fecha límite de PR
  abierto el miércoles.
- **HUs de front y back partidas:** #23 quedó con foto en el front y sin
  validación en el back; #42 tiene buscador en el front pero la API solo filtra
  por nombre. Propuesta: cada HU define su contrato de API antes de empezar.
- **Datos de demo improvisados:** se resolvió con `preparar_demo`, pero debería
  existir desde el sprint anterior.
- **Latencia de la base en USA-W:** medir y, si sigue, evaluar región.

**Acciones (con dueño y para cuándo)**
1. Mergear el PR #79 tras la revisión pendiente. — dueño del PR.
2. Abrir PR de la rama de #35 y decidir alcance (causas + cola manual). —
   Luciano / Nicolás.
3. Implementar #23 completa (backend + tests). — siguiente sprint.
4. Correr `preparar_demo` en el ensayo del próximo sprint y mantenerlo. — datos.

---

## 8. Después de la demo

```bash
# dejar la base de desarrollo limpia
cd backend
python manage.py preparar_demo --confirmar-desarrollo   # restaura estados
```

Y si se usó SQLite local para la demo: borrar `db.sqlite3` o dejarlo, está
ignorado por Git; no se sube nada.
