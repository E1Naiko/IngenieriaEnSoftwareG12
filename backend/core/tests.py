"""
Tests de los modelos de ``core`` (esquema del diagrama de BD).

Cubren las reglas que el diagrama impone y que la app ``crudComercios``
no toca: autogenerados (``token``, ``cod_seguimiento``), unicidad de DNI,
los estados de ``repartidor`` (con ``baja``), las FK de ``paquete`` y la
decisión del scrum 23/10 de **no** tener vínculo directo comercio ↔ cliente.

Ejecutar::

    cd backend
    python manage.py test core
"""

from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from .models import Cliente, Comercio, Comprobante, Paquete, Repartidor


def _comercio(**kwargs):
    defaults = {"nombre": "Kiosco Central", "telefono": "221-555-0100", "direccion": "Calle 7 #123"}
    defaults.update(kwargs)
    return Comercio.objects.create(**defaults)


def _cliente(**kwargs):
    defaults = {"telefono": "221-555-0200", "direccion": "Calle 44 #999", "dni": 30111222}
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


class RepartidorTests(TestCase):
    """repartidor: token autogenerado, DNI único y estados."""

    def test_token_se_autogenera_de_6(self):
        repartidor = _repartidor()
        self.assertRegex(repartidor.token, r"^[A-Z0-9]{6}$")

    def test_dni_unico(self):
        _repartidor(dni=20333444)
        with self.assertRaises(IntegrityError), transaction.atomic():
            _repartidor(dni=20333444, nombre="Otro", apellido="Otro")

    def test_estado_baja_disponible(self):
        """El scrum 23/10 pidió el estado BAJA (HU #25 dar de baja repartidor)."""
        repartidor = _repartidor(estado=Repartidor.Estado.BAJA)
        repartidor.refresh_from_db()
        self.assertEqual(repartidor.estado, "baja")
        self.assertEqual(
            [e.value for e in Repartidor.Estado], ["activo", "inactivo", "baja"]
        )

    def test_estado_por_defecto_activo(self):
        self.assertEqual(_repartidor().estado, Repartidor.Estado.ACTIVO)

    def test_listado_e_historial_como_properties(self):
        """Los campos REVISAR del diagrama se resuelven por relación inversa."""
        repartidor = _repartidor()
        comercio, cliente = _comercio(), _cliente()
        pendiente = Paquete.objects.create(comercio=comercio, cliente=cliente, repartidor=repartidor)
        entregado = Paquete.objects.create(
            comercio=comercio,
            cliente=cliente,
            repartidor=repartidor,
            estado=Paquete.Estado.ENTREGADO,
        )

        self.assertEqual(
            sorted(repartidor.listado_id_pedidos_asignados), sorted([pendiente.id, entregado.id])
        )
        self.assertEqual(list(repartidor.historial_asociado), [entregado])


class ComercioClienteTests(TestCase):
    """Comercio y Cliente son tablas independientes desde el cambio de esquema."""

    def test_cliente_se_crea_sin_comercio(self):
        cliente = _cliente()
        self.assertIsNotNone(cliente.pk)
        self.assertFalse(hasattr(cliente, "comercio"))

    def test_comercio_sin_datos_cliente(self):
        comercio = _comercio()
        self.assertFalse(hasattr(comercio, "datos_cliente"))
        self.assertEqual(
            {f.name for f in Comercio._meta.get_fields() if f.concrete},
            {"id", "nombre", "telefono", "direccion"},
        )

    def test_cliente_sin_campos_extra(self):
        self.assertEqual(
            {f.name for f in Cliente._meta.get_fields() if f.concrete},
            {"id", "telefono", "direccion", "dni"},
        )

    def test_vinculo_se_infiere_por_paquete(self):
        """Comercio ↔ cliente se consulta a través de Paquete (no hay FK directa)."""
        comercio, cliente = _comercio(), _cliente()
        Paquete.objects.create(comercio=comercio, cliente=cliente)

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
        p1 = Paquete.objects.create(comercio=self.comercio, cliente=self.cliente)
        p2 = Paquete.objects.create(comercio=self.comercio, cliente=self.cliente)
        self.assertRegex(p1.cod_seguimiento, r"^SRFR-[0-9A-F]{8}$")
        self.assertNotEqual(p1.cod_seguimiento, p2.cod_seguimiento)

    def test_estado_por_defecto_pendiente(self):
        paquete = Paquete.objects.create(comercio=self.comercio, cliente=self.cliente)
        self.assertEqual(paquete.estado, Paquete.Estado.PENDIENTE)

    def test_repartidor_opcional(self):
        """?<>? del diagrama: un paquete puede nacer sin repartidor asignado."""
        paquete = Paquete.objects.create(comercio=self.comercio, cliente=self.cliente)
        self.assertIsNone(paquete.repartidor)

        repartidor = _repartidor()
        paquete.repartidor = repartidor
        paquete.save()
        self.assertEqual(repartidor.paquetes.count(), 1)

    def test_borrar_repartidor_deja_paquete_sin_asignar(self):
        repartidor = _repartidor()
        paquete = Paquete.objects.create(
            comercio=self.comercio, cliente=self.cliente, repartidor=repartidor
        )
        repartidor.delete()
        paquete.refresh_from_db()
        self.assertIsNone(paquete.repartidor)

    def test_no_se_borra_un_comercio_con_paquetes(self):
        Paquete.objects.create(comercio=self.comercio, cliente=self.cliente)
        with self.assertRaises(ProtectedError):
            self.comercio.delete()

    def test_no_se_borra_un_cliente_con_paquetes(self):
        Paquete.objects.create(comercio=self.comercio, cliente=self.cliente)
        with self.assertRaises(ProtectedError):
            self.cliente.delete()

    def test_comprobante_one_to_one(self):
        """?>? del diagrama: el comprobante es opcional y pertenece a un paquete."""
        paquete = Paquete.objects.create(comercio=self.comercio, cliente=self.cliente)
        self.assertIsNone(paquete.comprobante)

        comprobante = Comprobante.objects.create()
        paquete.comprobante = comprobante
        paquete.save()
        self.assertEqual(comprobante.paquete, paquete)


class TablasDelDiagramaTests(TestCase):
    """Los nombres de tabla del diagrama se conservan vía Meta.db_table."""

    def test_db_table(self):
        self.assertEqual(
            {m._meta.db_table for m in (Repartidor, Comercio, Cliente, Paquete, Comprobante)},
            {"repartidor", "comercio", "cliente", "paquete", "comprobante"},
        )
