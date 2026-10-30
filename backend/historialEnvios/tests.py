"""Tests de la HU #10: historial de envíos."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Cliente, Comercio, Paquete, Repartidor


class HistorialEnviosTests(TestCase):
    def setUp(self):
        # El coordinador es un usuario de Django. force_login simula que ya inició sesión.
        self.coordinador = get_user_model().objects.create_user(
            username="coord", password="1234"
        )

        self.ana = Repartidor.objects.create(
            nombre="Ana", apellido="Paz", dni=11111111,
            telefono="111", mail="ana@mail.com",
        )
        self.beto = Repartidor.objects.create(
            nombre="Beto", apellido="Gil", dni=22222222,
            telefono="222", mail="beto@mail.com", estado="baja",  # dado de baja
        )
        self.comercio = Comercio.objects.create(
            nombre="Kiosco", telefono="333", direccion="Calle 1"
        )
        self.cliente = Cliente.objects.create(
            nombre="Laura", apellido="Gómez", telefono="444",
            direccion="Calle 2", dni=33333333,
        )

        # Paquetes de Ana: uno entregado, uno cancelado (más reciente) y uno pendiente.
        self._paquete(self.ana, "entregado", date(2026, 10, 20))
        self._paquete(self.ana, "cancelado", date(2026, 10, 25))
        self._paquete(self.ana, "pendiente", date(2026, 10, 28))
        # Paquete de Beto con el estado en MAYÚSCULAS: tiene que contar igual.
        self._paquete(self.beto, "ENTREGADO", date(2026, 10, 21))

    def _paquete(self, repartidor, estado, fecha_destino):
        return Paquete.objects.create(
            estado=estado,
            repartidor=repartidor,
            comercio=self.comercio,
            cliente=self.cliente,
            fecha_origen=date(2026, 10, 1),
            fecha_destino=fecha_destino,
        )

    def test_lista_de_repartidores(self):
        self.client.force_login(self.coordinador)
        r = self.client.get(reverse("historial-lista"))
        self.assertEqual(r.status_code, 200)

        data = r.json()
        self.assertEqual(data["count"], 2)  # también aparece el dado de baja
        por_id = {x["id"]: x for x in data["results"]}
        # Ana: entregado + cancelado (el pendiente no cuenta)
        self.assertEqual(por_id[self.ana.id]["cantidad_envios"], 2)
        self.assertFalse(por_id[self.ana.id]["dado_de_baja"])
        # Beto: su 'ENTREGADO' en mayúsculas cuenta
        self.assertEqual(por_id[self.beto.id]["cantidad_envios"], 1)
        self.assertTrue(por_id[self.beto.id]["dado_de_baja"])

    def test_historial_de_un_repartidor(self):
        self.client.force_login(self.coordinador)
        r = self.client.get(reverse("historial-repartidor", args=[self.ana.id]))
        self.assertEqual(r.status_code, 200)

        data = r.json()
        self.assertEqual(data["repartidor"]["id"], self.ana.id)
        self.assertEqual(data["count"], 2)  # el pendiente no entra
        # Del más reciente al más viejo (por fecha de destino)
        estados = [p["estado"] for p in data["results"]]
        self.assertEqual(estados, ["cancelado", "entregado"])

    def test_sin_sesion_responde_401(self):
        r1 = self.client.get(reverse("historial-lista"))
        r2 = self.client.get(reverse("historial-repartidor", args=[self.ana.id]))
        self.assertEqual(r1.status_code, 401)
        self.assertEqual(r2.status_code, 401)

    def test_repartidor_inexistente_responde_404(self):
        self.client.force_login(self.coordinador)
        r = self.client.get(reverse("historial-repartidor", args=[9999]))
        self.assertEqual(r.status_code, 404)