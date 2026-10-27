"""
Tests de los modelos de ``core`` (esquema del diagrama de BD).

Cubren las reglas del esquema que la API de comercios no toca: los
autogenerados (``token``, ``cod_seguimiento``), la unicidad del DNI, los
estados del repartidor y del paquete, las FK de ``paquete`` (``PROTECT`` /
``SET_NULL`` y el uno a uno con el comprobante), la migración del estado
``retirado`` y que comercio y cliente sean tablas independientes que solo se
cruzan en ``paquete``.

Ejecutar::

    cd backend
    DATABASE_MODE=sqlite python manage.py test core
"""

from datetime import date
import importlib

from django.apps import apps
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.forms import modelform_factory
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from .models import Cliente, Comercio, Comprobante, Paquete, Repartidor


def _comercio(**kwargs):
    defaults = {"nombre": "Kiosco Central", "telefono": "221-555-0100", "direccion": "Calle 7 #123"}
    defaults.update(kwargs)
    return Comercio.objects.create(**defaults)


def _cliente(**kwargs):
    defaults = {
        "nombre": "Juan",
        "apellido": "Pérez",
        "telefono": "221-555-0200",
        "direccion": "Calle 44 #999",
        "dni": 30111222,
    }
    defaults.update(kwargs)
    return Cliente.objects.create(**defaults)


def _repartidor(**kwargs):
    defaults = {
        "nombre": "Ana",
        "apellido": "Gómez",
        "dni": 20333444,
        "telefono": "221-555-0300",
        "mail": "ana@example.com",
    }
    defaults.update(kwargs)
    return Repartidor.objects.create(**defaults)


def _paquete(comercio, cliente, **kwargs):
    defaults = {
        "comercio": comercio,
        "cliente": cliente,
        "fecha_origen": date(2026, 10, 1),
        "fecha_destino": date(2026, 10, 2),
    }
    defaults.update(kwargs)
    return Paquete.objects.create(**defaults)


class RepartidorTests(TestCase):
    """Token autogenerado, DNI único y los tres estados posibles."""

    def test_token_se_autogenera_de_6(self):
        repartidor = _repartidor()
        self.assertRegex(repartidor.token, r"^[A-Z0-9]{6}$")

    def test_generador_estatico_de_token_reintenta_una_colision(self):
        _repartidor(token="AAAAAA")
        with patch("core.models.secrets.choice", side_effect=list("AAAAAABBBBBB")):
            self.assertEqual(Repartidor._generar_token(), "BBBBBB")

    def test_dni_unico(self):
        _repartidor(dni=20333444)
        with self.assertRaises(IntegrityError), transaction.atomic():
            _repartidor(dni=20333444, nombre="Otro", apellido="Otro")

    def test_estado_baja(self):
        """``baja`` es el estado definitivo de la HU #25 (dar de baja un repartidor)."""
        repartidor = _repartidor(estado=Repartidor.Estado.BAJA)
        repartidor.refresh_from_db()
        self.assertEqual(repartidor.estado, "baja")
        self.assertEqual(
            [e.value for e in Repartidor.Estado], ["activo", "inactivo", "baja"]
        )

    def test_estado_por_defecto_activo(self):
        self.assertEqual(_repartidor().estado, Repartidor.Estado.ACTIVO)

    def test_listado_e_historial_como_properties(self):
        """Los dos campos del diagrama que no son columna salen de la FK inversa."""
        repartidor = _repartidor()
        comercio, cliente = _comercio(), _cliente()
        pendiente = _paquete(comercio, cliente, repartidor=repartidor)
        retirado = _paquete(
            comercio,
            cliente,
            repartidor=repartidor,
            estado=Paquete.Estado.RETIRADO,
        )
        entregado = _paquete(
            comercio,
            cliente,
            repartidor=repartidor,
            estado=Paquete.Estado.ENTREGADO,
        )
        entregado_mayus = _paquete(
            comercio,
            cliente,
            repartidor=repartidor,
            estado="ENTREGADO",
        )

        self.assertEqual(
            sorted(repartidor.listado_id_pedidos_asignados),
            sorted([pendiente.id, retirado.id, entregado.id, entregado_mayus.id]),
        )
        self.assertEqual(
            sorted(p.id for p in repartidor.historial_asociado),
            sorted([entregado.id, entregado_mayus.id]),
        )


class ComercioClienteTests(TestCase):
    """Tablas independientes: ninguna de las dos apunta a la otra."""

    def test_cliente_se_crea_sin_comercio(self):
        """Un cliente se da de alto solo, sin necesitar un comercio primero."""
        cliente = _cliente()
        self.assertIsNotNone(cliente.pk)
        self.assertFalse(hasattr(cliente, "comercio"))

    def test_str_comercio_devuelve_el_nombre(self):
        self.assertEqual(str(_comercio()), "Kiosco Central")

    def test_comercio_tiene_cuatro_columnas(self):
        """``comercio`` = id + nombre + telefono + direccion, y nada más."""
        comercio = _comercio()
        self.assertFalse(hasattr(comercio, "datos_cliente"))
        self.assertEqual(
            {f.name for f in Comercio._meta.get_fields() if f.concrete},
            {"id", "nombre", "telefono", "direccion"},
        )

    def test_cliente_tiene_seis_columnas(self):
        """``cliente`` = id + nombre + apellido + telefono + direccion + dni."""
        self.assertEqual(
            {f.name for f in Cliente._meta.get_fields() if f.concrete},
            {"id", "nombre", "apellido", "telefono", "direccion", "dni"},
        )

    def test_cliente_guarda_nombre_y_apellido(self):
        cliente = _cliente(nombre="María", apellido="Gómez", dni=33444555)
        cliente.refresh_from_db()
        self.assertEqual(cliente.nombre, "María")
        self.assertEqual(cliente.apellido, "Gómez")
        self.assertIn("Gómez, María", str(cliente))

    def test_migracion_completa_nombre_y_apellido_faltantes(self):
        migracion = importlib.import_module(
            "core.migrations.0007_agregar_nombre_y_apellido_cliente"
        )
        sin_datos = _cliente(nombre="", apellido="", dni=31000001)
        con_datos = _cliente(nombre="Laura", apellido="Díaz", dni=31000002)

        migracion.popular_nombre_y_apellido_clientes(apps, connection.schema_editor())

        sin_datos.refresh_from_db()
        con_datos.refresh_from_db()
        self.assertTrue(sin_datos.nombre)
        self.assertTrue(sin_datos.apellido)
        self.assertEqual(con_datos.nombre, "Laura")
        self.assertEqual(con_datos.apellido, "Díaz")

    def test_vinculo_se_infiere_por_paquete(self):
        """El par comercio-cliente existe únicamente dentro de un paquete."""
        comercio, cliente = _comercio(), _cliente()
        _paquete(comercio, cliente)

        self.assertEqual(
            list(Paquete.objects.filter(comercio=comercio, cliente=cliente).values_list(
                "cod_seguimiento", flat=True
            )),
            [cliente.paquetes.get().cod_seguimiento],
        )


class PaqueteTests(TestCase):
    """paquete: FK, código de seguimiento y uno a uno con comprobante."""

    def setUp(self):
        self.comercio = _comercio()
        self.cliente = _cliente()

    def test_cod_seguimiento_autogenerado_unico(self):
        p1 = _paquete(self.comercio, self.cliente)
        p2 = _paquete(self.comercio, self.cliente)
        self.assertRegex(p1.cod_seguimiento, r"^SRFR-[0-9A-F]{8}$")
        self.assertNotEqual(p1.cod_seguimiento, p2.cod_seguimiento)

    def test_generador_estatico_de_codigo_reintenta_una_colision(self):
        _paquete(self.comercio, self.cliente, cod_seguimiento="SRFR-AAAAAAAA")
        with patch("core.models.secrets.token_hex", side_effect=["aaaaaaaa", "bbbbbbbb"]):
            self.assertEqual(Paquete._generar_codigo(), "SRFR-BBBBBBBB")

    def test_estado_por_defecto_pendiente(self):
        paquete = _paquete(self.comercio, self.cliente)
        self.assertEqual(paquete.estado, Paquete.Estado.PENDIENTE)

    def test_estado_retirado(self):
        paquete = _paquete(
            self.comercio, self.cliente, estado=Paquete.Estado.RETIRADO
        )
        paquete.refresh_from_db()
        self.assertEqual(paquete.estado, "retirado")

    def test_fechas_origen_y_destino_se_persisten(self):
        paquete = _paquete(self.comercio, self.cliente)
        paquete.refresh_from_db()
        self.assertEqual(paquete.fecha_origen, date(2026, 10, 1))
        self.assertEqual(paquete.fecha_destino, date(2026, 10, 2))

    def test_repartidor_opcional(self):
        """El paquete puede crearse antes de tener repartidor asignado."""
        paquete = _paquete(self.comercio, self.cliente)
        self.assertIsNone(paquete.repartidor)

        repartidor = _repartidor()
        paquete.repartidor = repartidor
        paquete.save()
        self.assertEqual(repartidor.paquetes.count(), 1)

    def test_borrar_repartidor_deja_paquete_sin_asignar(self):
        repartidor = _repartidor()
        paquete = _paquete(self.comercio, self.cliente, repartidor=repartidor)
        repartidor.delete()
        paquete.refresh_from_db()
        self.assertIsNone(paquete.repartidor)

    def test_no_se_borra_un_comercio_con_paquetes(self):
        _paquete(self.comercio, self.cliente)
        with self.assertRaises(ProtectedError):
            self.comercio.delete()

    def test_no_se_borra_un_cliente_con_paquetes(self):
        _paquete(self.comercio, self.cliente)
        with self.assertRaises(ProtectedError):
            self.cliente.delete()

    def test_comprobante_one_to_one(self):
        """El comprobante es opcional y lo sostiene la FK única de ``paquete``."""
        paquete = _paquete(self.comercio, self.cliente)
        self.assertIsNone(paquete.comprobante)

        comprobante = Comprobante.objects.create()  # `file` puede quedar vacío
        self.assertEqual(str(comprobante), f"Comprobante {comprobante.pk}")
        paquete.comprobante = comprobante
        paquete.save()
        self.assertEqual(comprobante.paquete, paquete)


class PaqueteAdminTests(TestCase):
    def test_admin_permite_guardar_y_filtrar_retirados(self):
        usuario = get_user_model().objects.create_superuser("admin", "admin@example.com", "clave")
        self.client.force_login(usuario)
        comercio, cliente = _comercio(), _cliente()
        paquete = _paquete(comercio, cliente)
        pendiente = _paquete(comercio, cliente)
        change_url = reverse("admin:core_paquete_change", args=[paquete.pk])

        respuesta = self.client.get(change_url)
        self.assertContains(respuesta, '<option value="retirado">Retirado</option>', html=True)

        respuesta = self.client.post(change_url, {
            "estado": "retirado",
            "tamanio": paquete.tamanio,
            "comercio": comercio.pk,
            "cliente": cliente.pk,
            "fecha_origen": "2026-10-01",
            "fecha_destino": "2026-10-02",
            "_save": "Guardar",
        })
        self.assertEqual(respuesta.status_code, 302)
        paquete.refresh_from_db()
        self.assertEqual(paquete.estado, Paquete.Estado.RETIRADO)

        respuesta = self.client.get(
            reverse("admin:core_paquete_changelist"), {"estado__exact": "retirado"}
        )
        self.assertContains(respuesta, paquete.cod_seguimiento)
        self.assertNotContains(respuesta, pendiente.cod_seguimiento)
        self.assertContains(respuesta, "Retirado")


class TablasDelDiagramaTests(TestCase):
    """Las tablas se llaman como en el diagrama, vía ``Meta.db_table``."""

    def test_db_table(self):
        modelos = (Repartidor, Comercio, Cliente, Paquete, Comprobante)
        self.assertEqual(
            {m._meta.db_table for m in modelos},
            {"repartidor", "comercio", "cliente", "paquete", "comprobante"},
        )

    def test_ids_son_enteros_de_32_bits(self):
        modelos = (Repartidor, Comercio, Cliente, Paquete, Comprobante)
        self.assertTrue(all(m._meta.pk.get_internal_type() == "AutoField" for m in modelos))

    def test_nombres_de_columnas_fk_en_paquete(self):
        columnas = {
            "repartidor": "id_repartidor_asignado",
            "comercio": "id_comercio",
            "cliente": "id_datos_cliente",
            "comprobante": "id_comprobante",
        }
        for campo, columna in columnas.items():
            with self.subTest(campo=campo):
                self.assertEqual(Paquete._meta.get_field(campo).column, columna)

    def test_fechas_obligatorias_y_file_de_255_caracteres(self):
        for nombre in ("fecha_origen", "fecha_destino"):
            with self.subTest(campo=nombre):
                self.assertFalse(Paquete._meta.get_field(nombre).null)
                self.assertEqual(Paquete._meta.get_field(nombre).get_internal_type(), "DateField")
        for nombre in ("nombre", "apellido"):
            with self.subTest(campo=f"cliente.{nombre}"):
                campo = Cliente._meta.get_field(nombre)
                self.assertFalse(campo.null)
                self.assertEqual(campo.get_internal_type(), "CharField")
                self.assertEqual(campo.max_length, 255)
        self.assertEqual(Comprobante._meta.get_field("file").max_length, 255)


class EstadoRetiradoMigrationTests(TransactionTestCase):
    """La migración registra los choices sin alterar los paquetes existentes."""

    migracion_anterior = [("core", "0005_actualizar_modelo_esquema")]
    migracion_nueva = [("core", "0006_agregar_estado_retirado_paquete")]

    def setUp(self):
        super().setUp()
        # Incluso si falla el test, las demás pruebas deben ver las migraciones actuales.
        self.addCleanup(self._restaurar_migraciones)
        executor = MigrationExecutor(connection)
        executor.migrate(self.migracion_anterior)
        apps_anteriores = executor.loader.project_state(self.migracion_anterior).apps
        ComercioAnterior = apps_anteriores.get_model("core", "Comercio")
        ClienteAnterior = apps_anteriores.get_model("core", "Cliente")
        PaqueteAnterior = apps_anteriores.get_model("core", "Paquete")
        self.choices_anteriores = dict(PaqueteAnterior._meta.get_field("estado").choices)

        comercio = ComercioAnterior.objects.create(
            nombre="Kiosco", telefono="123", direccion="Calle 1"
        )
        cliente = ClienteAnterior.objects.create(
            dni=30111222, telefono="456", direccion="Calle 2"
        )
        # También puede haber un 'retirado' guardado antes de esta migración:
        # choices no se valida automáticamente al guardar ni impone un CHECK en la BD.
        for numero, estado in enumerate(
            ("pendiente", "en_camino", "entregado", "cancelado", "retirado"), start=1
        ):
            PaqueteAnterior.objects.create(
                comercio=comercio,
                cliente=cliente,
                estado=estado,
                cod_seguimiento=f"SRFR-{numero:08X}",
                fecha_origen=date(2026, 10, 1),
                fecha_destino=date(2026, 10, 2),
            )
        self.filas_anteriores = self._filas_paquetes(PaqueteAnterior)

        executor = MigrationExecutor(connection)
        executor.migrate(self.migracion_nueva)
        self.apps_nuevas = executor.loader.project_state(self.migracion_nueva).apps

    def _restaurar_migraciones(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    @staticmethod
    def _filas_paquetes(modelo):
        return list(modelo.objects.order_by("pk").values(
            "id", "estado", "tamanio", "cod_seguimiento", "fecha_origen", "fecha_destino",
            "repartidor_id", "comercio_id", "cliente_id", "comprobante_id",
        ))

    def test_migracion_conserva_paquetes_y_actualiza_choices(self):
        PaqueteNuevo = self.apps_nuevas.get_model("core", "Paquete")
        campo = PaqueteNuevo._meta.get_field("estado")
        self.assertNotIn("retirado", self.choices_anteriores)
        self.assertEqual(
            dict(campo.choices), {**self.choices_anteriores, "retirado": "Retirado"}
        )
        self.assertEqual(campo.default, "pendiente")
        self.assertEqual(self._filas_paquetes(PaqueteNuevo), self.filas_anteriores)

    def test_reversion_conserva_los_datos_aunque_choices_vuelva_al_anterior(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migracion_anterior)
        apps_anteriores = executor.loader.project_state(self.migracion_anterior).apps
        PaqueteAnterior = apps_anteriores.get_model("core", "Paquete")
        self.assertNotIn("retirado", dict(PaqueteAnterior._meta.get_field("estado").choices))
        self.assertEqual(self._filas_paquetes(PaqueteAnterior), self.filas_anteriores)
