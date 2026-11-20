"""Pruebas del flujo entre repartidor saliente, reemplazo y coordinador."""

from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client as HttpClient, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Cliente, Comercio, Paquete, Repartidor


@override_settings(REASIGNACION_MINUTOS=15, REASIGNACION_RADIO_KM=5)
class ReasignacionTests(TestCase):
    ubicacion = {"latitud": -34.92, "longitud": -57.95}

    @classmethod
    def setUpTestData(cls):
        cls.original = Repartidor.objects.create(dni=11, tipo_vehiculo="auto")
        cls.vecino = Repartidor.objects.create(dni=22, tipo_vehiculo="auto")
        cls.otro = Repartidor.objects.create(dni=33, tipo_vehiculo="auto")
        cls.moto = Repartidor.objects.create(dni=44, tipo_vehiculo="moto")
        cls.inactivo = Repartidor.objects.create(dni=55, estado="inactivo", tipo_vehiculo="auto")
        cls.coordinador = get_user_model().objects.create_user("coordinador", password="prueba-local")
        cls.paquete = Paquete.objects.create(
            estado="EN_CAMINO",
            repartidor=cls.original,
            comercio=Comercio.objects.create(nombre="Comercio", direccion="Calle 55"),
            cliente=Cliente.objects.create(dni=66, nombre="Ana", direccion="Calle 7"),
            fecha_origen=date(2026, 11, 19), fecha_destino=date(2026, 11, 20),
            tamanio=Paquete.Tamanio.MEDIANO,
        )

    def _post(self, nombre, datos, cliente=None, **headers):
        return (cliente or self.client).post(reverse(nombre), datos, content_type="application/json", **headers)

    def _cancelar(self, **cambios):
        return self._post("cambiar-estado-pedido", {
            "id": self.paquete.pk, "estado": "cancelado", "token": self.original.token,
            "causa": "fuerza_mayor", "motivo": " Accidente ", "ubicacion": self.ubicacion,
            **cambios,
        })

    def _cercanos(self, repartidor, tomar=False, **cambios):
        datos = {"token": repartidor.token, "ubicacion": self.ubicacion, **cambios}
        if tomar:
            datos["id"] = self.paquete.pk
        return self._post("pedidos-cercanos", datos)

    def _en_cola_manual(self):
        return self.client.get(reverse("paquetesEnCurso")).json()["paquetes"][0]["por_reasignar"]

    def _cola_manual(self):
        return self.client.get(reverse("pedidos-por-reasignar"))

    def _asignar(self, repartidor, **kwargs):
        return self._post("asignarRepartidor", {"paquete": self.paquete.pk, "repartidor": repartidor.pk}, **kwargs)

    def test_publica_y_libera_para_otro_repartidor_cercano(self):
        ahora = timezone.now()
        with patch("verPedidosPorAsignar.services.timezone.now", return_value=ahora):
            respuesta = self._cancelar()
        self.assertEqual(respuesta.status_code, 200)
        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.estado, Paquete.Estado.PENDIENTE_REASIGNACION)
        self.assertIsNone(self.paquete.repartidor_id)
        self.assertEqual(self.paquete.repartidor_original_id, self.original.pk)
        self.assertEqual(self.paquete.motivo_cancelacion, "Accidente")
        self.assertEqual(self.paquete.reasignacion_hasta, ahora + timedelta(minutes=15))
        self.assertFalse(self._en_cola_manual())
        self.assertEqual(self._cola_manual().status_code, 403)
        self.client.force_login(self.coordinador)
        self.assertEqual(self._cola_manual().json(), {"paquetes": []})
        oferta, = self._cercanos(self.vecino).json()["paquetes"]
        self.assertEqual(oferta["id"], self.paquete.pk)
        self.assertNotIn("direccion", oferta)
        self.assertNotIn("retiro", oferta)
        self.assertEqual(self._post("paquetes-repartidor", {"token": self.original.token}).json()["paquetes"], [])

        self.assertEqual(self._cercanos(self.vecino, tomar=True).status_code, 200)
        self.assertEqual(self._cercanos(self.otro, tomar=True).status_code, 409)
        self.assertEqual(self._cercanos(self.otro).json()["paquetes"], [])
        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.repartidor_id, self.vecino.pk)
        self.assertEqual(self.paquete.estado, Paquete.Estado.ASIGNADO)
        self.assertEqual(self._cancelar().status_code, 403)
        asignado, = self._post("paquetes-repartidor", {"token": self.vecino.token}).json()["paquetes"]
        self.assertEqual(asignado["retiro"], self.ubicacion)

    def test_oferta_no_disponible_para_original_lejano_o_vehiculo_insuficiente(self):
        self.assertEqual(self._cancelar().status_code, 200)
        for repartidor, ubicacion in (
            (self.original, self.ubicacion), (self.moto, self.ubicacion),
            (self.vecino, {"latitud": -35.1, "longitud": -57.95}),
        ):
            with self.subTest(repartidor=repartidor.pk):
                self.assertEqual(self._cercanos(repartidor, ubicacion=ubicacion).json()["paquetes"], [])
                self.assertEqual(self._cercanos(repartidor, tomar=True, ubicacion=ubicacion).status_code, 409)
        self.assertEqual(self._cercanos(self.inactivo).status_code, 403)
        self.assertEqual(self._cercanos(self.vecino, tomar=True, token="INVALIDO").status_code, 401)

    def test_vencimiento_habilita_al_coordinador_y_cierra_la_oferta_en_el_limite(self):
        self.assertEqual(self._cancelar().status_code, 200)
        self.paquete.refresh_from_db()
        self.assertEqual(self._asignar(self.vecino).status_code, 403)
        self.client.force_login(self.coordinador)
        self.assertEqual(self._asignar(self.vecino).status_code, 409)
        with patch("django.utils.timezone.now", return_value=self.paquete.reasignacion_hasta):
            self.assertTrue(self._en_cola_manual())
            publicado, = self._cola_manual().json()["paquetes"]
            self.assertEqual(publicado["id"], self.paquete.pk)
            self.assertEqual(publicado["motivo_cancelacion"], "Accidente")
            self.assertEqual(self._cercanos(self.vecino).json()["paquetes"], [])
            self.assertEqual(self._cercanos(self.vecino, tomar=True).status_code, 409)
            url = reverse("asignarRepartidor")
            self.assertEqual(HttpClient().get(url, {"paquete": self.paquete.pk}).status_code, 403)
            con_csrf = HttpClient(enforce_csrf_checks=True)
            login = self._post("login-coordinador", {"username": "coordinador", "password": "prueba-local"}, cliente=con_csrf)
            self.assertEqual(login.status_code, 200)
            data = con_csrf.get(url, {"paquete": self.paquete.pk}).json()
            self.assertEqual({r["id"] for r in data["repartidores"]}, {self.vecino.pk, self.otro.pk})
            self.assertEqual(data["motivo_cancelacion"], "Accidente")
            self.assertEqual(self._asignar(self.vecino, cliente=con_csrf).status_code, 403)
            csrf = {"HTTP_X_CSRFTOKEN": data["csrf_token"], "HTTP_ORIGIN": "http://testserver"}
            self.assertEqual(self._asignar(self.original, cliente=con_csrf, **csrf).status_code, 400)
            self.assertEqual(self._asignar(self.vecino, cliente=con_csrf, **csrf).status_code, 200)
            self.assertEqual(self._asignar(self.otro, cliente=con_csrf, **csrf).status_code, 409)
            self.assertEqual(self._cola_manual().json(), {"paquetes": []})
        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.repartidor_id, self.vecino.pk)
        self.assertIsNone(self.paquete.reasignacion_hasta)

    def test_desplegable_deriva_a_cola_manual_sin_gps(self):
        respuesta = self._post("cambiar-estado-pedido", {
            "id": self.paquete.pk,
            "token": self.original.token,
            "estado": "pendiente_reasignacion",
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(self._en_cola_manual())
        self.assertEqual(self._cercanos(self.vecino).json()["paquetes"], [])

    def test_estado_directo_con_ubicacion_publica_la_oferta(self):
        respuesta = self._post("cambiar-estado-pedido", {
            "id": self.paquete.pk,
            "token": self.original.token,
            "estado": "pendiente_reasignacion",
            "ubicacion": self.ubicacion,
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(self._en_cola_manual())
        oferta, = self._cercanos(self.vecino).json()["paquetes"]
        self.assertEqual(oferta["id"], self.paquete.pk)

    def test_sin_ubicacion_pasa_directo_al_coordinador(self):
        self.assertEqual(self._cancelar(ubicacion=None).status_code, 200)
        self.assertTrue(self._en_cola_manual())
        self.client.force_login(self.coordinador)
        self.assertEqual([p["id"] for p in self._cola_manual().json()["paquetes"]], [self.paquete.pk])
        self.assertEqual(self._cercanos(self.vecino).json()["paquetes"], [])

    def test_ausencia_o_rechazo_se_devuelve_al_comercio_sin_oferta(self):
        """Ni la ausencia ni el rechazo del cliente se reasignan: vuelven al origen.

        Se distinguen por estado: ``en_devolucion`` (ausente, el repartidor
        confirma la entrega en el comercio) y ``cancelado_por_cliente``
        (rechazo, ya cerrado con el paquete en manos del repartidor).
        """
        self.client.force_login(self.coordinador)
        esperado = {
            "cliente_ausente": Paquete.Estado.EN_DEVOLUCION,
            "cliente_rechaza": Paquete.Estado.CANCELADO_POR_CLIENTE,
        }
        for causa, estado_esperado in esperado.items():
            with self.subTest(causa=causa):
                Paquete.objects.filter(pk=self.paquete.pk).update(estado=Paquete.Estado.EN_CAMINO)
                self.assertEqual(self._cancelar(causa=causa).status_code, 200)
                self.paquete.refresh_from_db()
                self.assertEqual(self.paquete.estado, estado_esperado)
                # El paquete sigue a cargo del repartidor, sin oferta ni cola manual.
                self.assertEqual(self.paquete.repartidor_id, self.original.pk)
                self.assertIsNone(self.paquete.reasignacion_hasta)
                self.assertIsNone(self.paquete.retiro_latitud)
                self.assertEqual(self._cola_manual().json(), {"paquetes": []})
                self.assertEqual(self._cercanos(self.vecino).json()["paquetes"], [])

                # El repartidor lo sigue viendo en su lista y sabe adónde llevarlo.
                paquetes = self._post("paquetes-repartidor", {"token": self.original.token}).json()["paquetes"]
                self.assertEqual(len(paquetes), 1)
                self.assertEqual(paquetes[0]["direccion_comercio"], "Calle 55")

                confirmacion = self._post("cambiar-estado-pedido", {
                    "id": self.paquete.pk, "estado": "cancelado", "token": self.original.token,
                })
                self.paquete.refresh_from_db()
                if causa == "cliente_ausente":
                    # Ausente: se confirma la devolución y recién ahí se cierra.
                    self.assertEqual(confirmacion.status_code, 200)
                    self.assertEqual(self.paquete.estado, Paquete.Estado.CANCELADO)
                else:
                    # Rechazo: ya estaba cerrado, no admite cambios.
                    self.assertEqual(confirmacion.status_code, 400)
                    self.assertEqual(self.paquete.estado, Paquete.Estado.CANCELADO_POR_CLIENTE)

    def test_valida_motivo_causa_ubicacion_y_titularidad(self):
        for cambios, status in (
            ({"motivo": " "}, 400), ({"causa": None}, 400), ({"motivo": "x" * 501}, 400),
            ({"ubicacion": {"latitud": 999, "longitud": 50}}, 400),
            ({"token": ""}, 401), ({"token": self.vecino.token}, 403),
            ({"estado": "pendiente_reasignacion"}, 400),
        ):
            with self.subTest(cambios=cambios):
                self.assertEqual(self._cancelar(**cambios).status_code, status)
        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.estado, "EN_CAMINO")
        self.assertEqual(self.paquete.repartidor_id, self.original.pk)

    def test_no_publica_un_pedido_entregado(self):
        paquetes = Paquete.objects.filter(pk=self.paquete.pk)
        paquetes.update(estado="ENTREGADO")
        self.assertEqual(self._cancelar().status_code, 400)
        self.assertEqual(self._cercanos(self.vecino).json()["paquetes"], [])

    def test_solo_fuerza_mayor_vuelve_a_la_flota(self):
        """Los tres desenlaces: reasignar, devolver y cierre por rechazo."""
        desenlaces = {
            "fuerza_mayor": Paquete.Estado.PENDIENTE_REASIGNACION,
            "cliente_ausente": Paquete.Estado.EN_DEVOLUCION,
            "cliente_rechaza": Paquete.Estado.CANCELADO_POR_CLIENTE,
        }
        for causa, estado in desenlaces.items():
            with self.subTest(causa=causa):
                Paquete.objects.filter(pk=self.paquete.pk).update(
                    estado=Paquete.Estado.EN_CAMINO,
                    repartidor=self.original,
                    repartidor_original=None,
                )
                self.assertEqual(self._cancelar(causa=causa).status_code, 200)
                self.paquete.refresh_from_db()
                self.assertEqual(self.paquete.estado, estado)
                # Solo fuerza mayor libera el pedido y lo publica.
                se_reasigna = causa == "fuerza_mayor"
                self.assertEqual(self.paquete.repartidor_id is None, se_reasigna)
                self.assertEqual(
                    self.paquete.repartidor_original_id == self.original.pk, se_reasigna
                )
                ofertas = self._cercanos(self.vecino).json()["paquetes"]
                self.assertEqual(len(ofertas), 1 if se_reasigna else 0)
