"""Prepara (y restaura) los datos mínimos para la demo del Sprint 2.

Uso::

    cd backend
    python manage.py preparar_demo --confirmar-desarrollo

Por qué existe
--------------
- Los tokens de los repartidores no se pueden consultar en una lista: en el
  panel del coordinador se ven uno por uno, en el formulario de edición. El día
  de la demo nadie quiere buscar tres tokens a mano con el cliente mirando.
- El comando es **idempotente y restaurador**: si se corrió la demo de prueba y
  los paquetes quedaron en otros estados, volver a ejecutarlo deja todo como al
  inicio (incluidos los estados), sin duplicar registros.
- Los nombres y direcciones tienen tildes, ñ y teléfonos con guiones a
  propósito, para poder mostrar las búsquedas de las HU #41 y #42.

Seguridad
---------
Sigue el mismo criterio que ``cargar_repartidores_demo``: sin el flag
``--confirmar-desarrollo`` no hace nada. Está pensado para la base de
desarrollo; no usar contra producción.
"""

from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from core.models import Cliente, Comercio, Paquete, Repartidor

# --- Personas de la demo ---------------------------------------------------
# (dni, nombre, apellido, telefono, mail, tipo_vehiculo, estado)
REPARTIDORES = [
    (30111222, "Valentina", "Ruiz", "2215550001", "valen.demo@example.invalid",
     Repartidor.TipoVehiculo.MOTO, Repartidor.Estado.ACTIVO),
    (31222333, "Marcos", "Pérez", "2215550002", "marcos.demo@example.invalid",
     Repartidor.TipoVehiculo.AUTO, Repartidor.Estado.ACTIVO),
    # Dado de baja: sirve para mostrar (HU #38) que un repartidor de baja no
    # puede iniciar sesión ni cambiar su disponibilidad.
    (32333444, "Bruno", "Sosa", "2215550003", "bruno.demo@example.invalid",
     Repartidor.TipoVehiculo.CAMIONETA, Repartidor.Estado.BAJA),
]

# (nombre, telefono, direccion) — con tildes para el buscador de #42.
COMERCIOS = [
    ("Almacén Don José", "221-555-0100", "Calle 7 #123"),
    ("Panadería La Espiga", "221-555-0142", "Av. 51 #456"),
    ("Kiosco El Sol", "221-555-0177", "Diag. 74 #789"),
]

# (dni, nombre, apellido, telefono, direccion)
CLIENTES = [
    (33444555, "Ana", "Gómez", "2215550011", "Calle 12 #34"),
    (35666777, "Julián", "Fernández", "2215550012", "Av. 7 #890"),
    (38999000, "Sofía", "Martínez", "2215550013", "Calle 45 #67"),
]

# (codigo, cliente_dni, comercio_nombre, tamanio, estado, repartidor_dni|None)
# Los códigos fijos hacen que la demo sea repetible: los paquetes se buscan
# por ``cod_seguimiento`` y no se duplican.
PAQUETES = [
    # Pedidos "en curso" variados para el buscador de la HU #41.
    ("SRFR-DEMO0001", 33444555, "Almacén Don José", Paquete.Tamanio.MEDIANO,
     Paquete.Estado.EN_CAMINO, 30111222),
    ("SRFR-DEMO0002", 35666777, "Panadería La Espiga", Paquete.Tamanio.CHICO,
     Paquete.Estado.ASIGNADO, 31222333),
    # Sin repartidor: filtro "sin asignar" + flujo de asignación del coordinador.
    ("SRFR-DEMO0003", 38999000, "Kiosco El Sol", Paquete.Tamanio.GRANDE,
     Paquete.Estado.PENDIENTE, None),
    # Cancelados: es lo que lista "Por Reasignar" (HU #36). Dos, para poder
    # mostrar el 409 cuando dos repartidores aceptan a la vez.
    ("SRFR-DEMO0004", 33444555, "Almacén Don José", Paquete.Tamanio.MEDIANO,
     Paquete.Estado.CANCELADO, 31222333),
    ("SRFR-DEMO0005", 38999000, "Kiosco El Sol", Paquete.Tamanio.GRANDE,
     Paquete.Estado.CANCELADO, 30111222),
    # Entregado: NO debe aparecer en "Paquetes en curso" ni en "Por Reasignar".
    ("SRFR-DEMO0006", 35666777, "Panadería La Espiga", Paquete.Tamanio.CHICO,
     Paquete.Estado.ENTREGADO, 30111222),
    # Otro en camino del mismo repartidor: búsqueda por repartidor en #41.
    ("SRFR-DEMO0007", 38999000, "Av. 51 #456", Paquete.Tamanio.GRANDE,
     Paquete.Estado.EN_CAMINO, 30111222),
]


class Command(BaseCommand):
    help = (
        "Crea y restaura los datos de la demo del Sprint 2 (repartidores, "
        "comercios, clientes y paquetes) y muestra los tokens para la "
        "presentación. Idempotente: se puede volver a ejecutar."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirmar-desarrollo",
            action="store_true",
            help="Confirma que la base configurada es de pruebas, no de producción.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["confirmar_desarrollo"]:
            raise CommandError(
                "Solo para la demo en desarrollo. Verificá la base configurada "
                "con `python manage.py revisar_db` y volvé a ejecutar con "
                "--confirmar-desarrollo."
            )

        destino = self._destino_db()
        self.stdout.write(self.style.WARNING(f"Base en uso: {destino}"))

        repartidores = self._crear_repartidores()
        comercios = self._crear_comercios()
        clientes = self._crear_clientes()
        creados, actualizados = self._crear_paquetes(repartidores, clientes, comercios)

        self._resumen(creados, actualizados, repartidores, comercios, clientes)

    # ------------------------------------------------------------------ #
    def _destino_db(self):
        """Nombre del motor y del host, sin credenciales."""
        datos = connection.settings_dict
        motor = datos.get("ENGINE", "").rsplit(".", 1)[-1]
        host = datos.get("HOST") or "archivo local"
        nombre = datos.get("NAME") or ""
        if motor == "sqlite3":
            return f"sqlite3 ({nombre})"
        return f"{motor} en {host} / {nombre}"

    def _crear_repartidores(self):
        resultado = {}
        for dni, nombre, apellido, telefono, mail, vehiculo, estado in REPARTIDORES:
            repartidor, creado = Repartidor.objects.get_or_create(
                dni=dni,
                defaults={
                    "nombre": nombre,
                    "apellido": apellido,
                    "telefono": telefono,
                    "mail": mail,
                    "tipo_vehiculo": vehiculo,
                    "estado": estado,
                },
            )
            if creado:
                self.stdout.write(f"  + repartidor {apellido}, {nombre}")
            else:
                # Se restaura el estado para que la demo arranque siempre igual
                # (un ensayo puede haberlo dejado "inactivo" o "baja").
                cambios = []
                if repartidor.estado != estado:
                    repartidor.estado = estado
                    cambios.append("estado")
                if repartidor.tipo_vehiculo != vehiculo:
                    repartidor.tipo_vehiculo = vehiculo
                    cambios.append("tipo_vehiculo")
                if cambios:
                    repartidor.save(update_fields=cambios)
                    self.stdout.write(
                        f"  ~ repartidor {apellido}, {nombre} restaurado ({', '.join(cambios)})"
                    )
            resultado[dni] = repartidor
        return resultado

    def _crear_comercios(self):
        resultado = {}
        for nombre, telefono, direccion in COMERCIOS:
            comercio, creado = Comercio.objects.get_or_create(
                nombre=nombre,
                defaults={"telefono": telefono, "direccion": direccion},
            )
            if creado:
                self.stdout.write(f"  + comercio {nombre}")
            resultado[nombre] = comercio
        return resultado

    def _crear_clientes(self):
        resultado = {}
        for dni, nombre, apellido, telefono, direccion in CLIENTES:
            cliente, creado = Cliente.objects.get_or_create(
                dni=dni,
                defaults={
                    "nombre": nombre,
                    "apellido": apellido,
                    "telefono": telefono,
                    "direccion": direccion,
                },
            )
            if creado:
                self.stdout.write(f"  + cliente {apellido}, {nombre}")
            resultado[dni] = cliente
        return resultado

    def _crear_paquetes(self, repartidores, clientes, comercios):
        hoy = date.today()
        creados = actualizados = 0
        for codigo, dni, comercio_nombre, tamanio, estado, repartidor_dni in PAQUETES:
            # El comercio puede venir por nombre; hay un ítem con dirección
            # porque el modelo exige un Comercio y la lista muestra su
            # dirección como punto de retiro.
            comercio = comercios.get(comercio_nombre) or next(
                c for c in comercios.values() if c.direccion == comercio_nombre
            )
            paquete, creado = Paquete.objects.update_or_create(
                cod_seguimiento=codigo,
                defaults={
                    "cliente": clientes[dni],
                    "comercio": comercio,
                    "tamanio": tamanio,
                    "estado": estado,
                    "repartidor": repartidores.get(repartidor_dni) if repartidor_dni else None,
                    "fecha_origen": hoy,
                    "fecha_destino": hoy + timedelta(days=2),
                },
            )
            if creado:
                creados += 1
                self.stdout.write(f"  + paquete {codigo} ({estado})")
            else:
                actualizados += 1
        return creados, actualizados

    def _resumen(self, creados, actualizados, repartidores, comercios, clientes):
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Paquetes: {creados} creados, {actualizados} restaurados "
            f"(total demo: {len(PAQUETES)})."
        ))
        self.stdout.write(
            f"Comercios: {len(comercios)} · Clientes: {len(clientes)} · "
            f"Repartidores: {len(repartidores)}"
        )

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Tokens para la demo"))
        for dni, nombre, apellido, *_ in REPARTIDORES:
            repartidor = repartidores[dni]
            self.stdout.write(
                f"  {nombre} {apellido:<10} DNI {dni}  →  token {repartidor.token}"
                f"   [{repartidor.estado}]"
            )

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Guion rápido"))
        self.stdout.write("  #41/#42 (coordinador): buscar 'gomez', 'en camino', '221-555-01'.")
        self.stdout.write("  #22 (repartidor): pasar de Disponible a No disponible y ver la flota.")
        self.stdout.write("  #36: con el token de Marcos, 'Pedidos por Reasignar' → 2 pedidos.")
        self.stdout.write("  #39 (coordinador): editar un repartidor y repetir un DNI.")
        self.stdout.write(
            "  #23: entregar SRFR-DEMO0002 (cliente DNI 35666777) sin DNI, con DNI"
            " ajeno y con el correcto."
        )
        self.stdout.write("  #38: iniciar sesión con el token de Bruno → rechazado (dado de baja).")
        self.stdout.write("")
        self.stdout.write(
            "Recordatorio: verificá que exista el usuario del coordinador "
            "(createsuperuser) y que `python manage.py migrate` esté al día."
        )
