"""
Tests de integración de ``GET /api/dashboard/paquetes-en-curso/``.

Ejercitan la vista a través del cliente de pruebas de Django, con la base de
test aislada que crea ``TestCase``. Ejecutar::

    cd backend
    DATABASE_MODE=sqlite python manage.py test paquetesEnCurso

El contrato JSON es el que consume ``frontend/src/pages/PaquetesEnCurso.tsx``:
cada ítem tiene ``id``, ``destinatario``, ``direccion``, ``repartidor`` y
``estado`` (valores primitivos, nunca instancias de modelos). El único estado
excluido es ``entregado``: ``cancelado`` es intermediario y debe aparecer.
"""

from datetime import date

from django.test import Client, TestCase
from django.urls import reverse

from core.models import Cliente, Comercio, Paquete, Repartidor

from .views import MSG_NO_HAY_PAQUETES_ACTIVOS


class PaquetesEnCursoAPITests(TestCase):
    """Listado de paquetes activos que muestra el panel del coordinador."""

    @classmethod
    def setUpTestData(cls):
        cls.comercio = Comercio.objects.create(
            nombre="Kiosco Central",
            telefono="221-555-0100",
            direccion="Calle 7 #123",
        )
        cls.cliente = Cliente.objects.create(
            nombre="Ana",
            apellido="Pérez",
            dni=30111222,
            telefono="221-555-0200",
            direccion="Calle 12 #34",
        )
        cls.repartidor = Repartidor.objects.create(
            nombre="Juan",
            apellido="Gómez",
            dni=40111222,
            telefono="221-555-0300",
            mail="juan@example.com",
        )

        def crear_paquete(estado, repartidor=None):
            return Paquete.objects.create(
                comercio=cls.comercio,
                cliente=cls.cliente,
                repartidor=repartidor,
                estado=estado,
                fecha_origen=date(2026, 10, 20),
                fecha_destino=date(2026, 10, 27),
            )

        cls.en_camino = crear_paquete(Paquete.Estado.EN_CAMINO, cls.repartidor)
        cls.pendiente = crear_paquete(Paquete.Estado.PENDIENTE)
        cls.retirado = crear_paquete(Paquete.Estado.RETIRADO, cls.repartidor)
        cls.cancelado = crear_paquete(Paquete.Estado.CANCELADO, cls.repartidor)
        crear_paquete(Paquete.Estado.ENTREGADO, cls.repartidor)

    def url(self):
        return reverse("paquetesEnCurso")

    def test_get_devuelve_200_y_el_contrato_del_frontend(self):
        """200, sin 500 por select_related inválido ni por FKs no serializables."""
        resp = self.client.get(self.url())

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(set(data), {"paquetes"})

        por_id = {item["id"]: item for item in data["paquetes"]}
        self.assertEqual(
            set(por_id),
            {
                self.en_camino.id,
                self.pendiente.id,
                self.retirado.id,
                self.cancelado.id,
            },
        )

        item = por_id[self.en_camino.id]
        self.assertEqual(
            set(item),
            {"id", "destinatario", "direccion", "repartidor", "estado"},
        )
        self.assertEqual(item["destinatario"], "Ana Pérez")
        self.assertEqual(item["direccion"], "Calle 12 #34")
        self.assertEqual(item["repartidor"], "Juan Gómez")
        self.assertEqual(item["estado"], Paquete.Estado.EN_CAMINO)

    def test_cancelado_se_lista_porque_es_un_estado_intermediario(self):
        """Solo 'entregado' es estado final: 'cancelado' sigue en el panel."""
        resp = self.client.get(self.url())

        self.assertEqual(resp.status_code, 200)
        estados = {item["id"]: item["estado"] for item in resp.json()["paquetes"]}
        self.assertEqual(estados[self.cancelado.id], Paquete.Estado.CANCELADO)

    def test_entregado_en_mayusculas_se_excluye_y_cancelado_permanece(self):
        """La BD es varchar: 'ENTREGADO' se excluye; 'CANCELADO' se sigue listando."""
        Paquete.objects.filter(pk=self.en_camino.pk).update(estado="ENTREGADO")
        Paquete.objects.filter(pk=self.cancelado.pk).update(estado="CANCELADO")

        resp = self.client.get(self.url())

        self.assertEqual(resp.status_code, 200)
        paquetes = {item["id"]: item for item in resp.json()["paquetes"]}
        self.assertEqual(
            set(paquetes),
            {self.pendiente.id, self.retirado.id, self.cancelado.id},
        )
        self.assertEqual(paquetes[self.cancelado.id]["estado"], "CANCELADO")

    def test_paquete_sin_repartidor_devuelve_texto_y_no_null(self):
        resp = self.client.get(self.url())

        item = next(
            p for p in resp.json()["paquetes"] if p["id"] == self.pendiente.id
        )
        self.assertEqual(item["repartidor"], "Sin asignar")

    def test_sin_paquetes_activos_devuelve_lista_vacia_y_mensaje(self):
        Paquete.objects.all().delete()

        resp = self.client.get(self.url())

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {"mensaje": MSG_NO_HAY_PAQUETES_ACTIVOS, "paquetes": []},
        )

    def test_metodo_distinto_de_get_devuelve_405(self):
        """Con CSRF activado (como en el servidor real) el POST da 405, no 403."""
        cliente = Client(enforce_csrf_checks=True)
        resp = cliente.post(self.url())

        self.assertEqual(resp.status_code, 405)
        self.assertEqual(resp.json(), {"error": "Método no permitido."})

    def test_una_sola_consulta_gracias_a_select_related(self):
        """Las FKs se resuelven en el JOIN: no hay una query por paquete."""
        with self.assertNumQueries(1):
            resp = self.client.get(self.url())

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["paquetes"]), 4)
