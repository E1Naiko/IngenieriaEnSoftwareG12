"""Tests de la HU #17: ver pedidos asignados."""
import datetime
import json

from django.test import TestCase
from django.urls import reverse

from core.models import Cliente, Comercio, Paquete, Repartidor


class PedidosAsignadosTests(TestCase):
    def setUp(self):
        self.url = reverse("paquetes-repartidor")
        self.repartidor = Repartidor.objects.create(
            nombre="Ana", apellido="Paz", dni=11111111,
            telefono="123", mail="ana@mail.com",
        )
        self.otro = Repartidor.objects.create(
            nombre="Luis", apellido="Sosa", dni=22222222,
            telefono="456", mail="luis@mail.com",
        )
        self.comercio = Comercio.objects.create(nombre="Kiosco", telefono="1", direccion="Calle 1")
        self.cliente = Cliente.objects.create(
            nombre="Juan", apellido="Pérez", telefono="2", direccion="Calle 2", dni=33333333,
        )

    def _paquete(self, repartidor, estado=Paquete.Estado.PENDIENTE):
        return Paquete.objects.create(
            repartidor=repartidor, comercio=self.comercio, cliente=self.cliente,
            estado=estado,
            fecha_origen=datetime.date(2026, 10, 29),
            fecha_destino=datetime.date(2026, 10, 30),
        )

    def _post(self, payload):
        return self.client.post(
            self.url, data=json.dumps(payload), content_type="application/json"
        )

    def test_escenario_1_lista_solo_sus_pedidos_activos(self):
        asignado = self._paquete(self.repartidor, "ASIGNADO")  # como los datos DEV
        retirado = self._paquete(self.repartidor, "RETIRADO")
        en_camino = self._paquete(self.repartidor, Paquete.Estado.EN_CAMINO)
        # Ninguno de estos debe aparecer
        self._paquete(self.repartidor, Paquete.Estado.PENDIENTE)
        self._paquete(self.repartidor, "ENTREGADO")
        self._paquete(self.repartidor, Paquete.Estado.CANCELADO)
        self._paquete(self.otro, Paquete.Estado.RETIRADO)
        self._paquete(None, Paquete.Estado.RETIRADO)

        r = self._post({"token": self.repartidor.token})
        self.assertEqual(r.status_code, 200)
        paquetes = r.json()["paquetes"]
        self.assertEqual(
            {p["id"] for p in paquetes}, {asignado.id, retirado.id, en_camino.id}
        )
        self.assertEqual(paquetes[2]["estado"], "asignado")
        self.assertEqual(paquetes[0], {
            "id": en_camino.id,  # orden -id: el más nuevo primero
            "cod_seguimiento": en_camino.cod_seguimiento,
            "estado": "en_camino",
            "tamanio": "chico",
            "destinatario": "Juan Pérez",
            "direccion": "Calle 2",
            "comercio": "Kiosco",
            "fecha_destino": "2026-10-30",
        })

    def test_escenario_2_sin_pedidos(self):
        r = self._post({"token": self.repartidor.token})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["paquetes"], [])

    def test_token_inexistente(self):
        r = self._post({"token": "ZZZZZZ"})
        self.assertEqual(r.status_code, 404)
        self.assertIn("message", r.json())

    def test_repartidor_dado_de_baja(self):
        self.repartidor.estado = Repartidor.Estado.BAJA
        self.repartidor.save()
        r = self._post({"token": self.repartidor.token})
        self.assertEqual(r.status_code, 403)
        self.assertIn("message", r.json())

    def test_get_no_permitido(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
