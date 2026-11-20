"""Tests de la HU #38: baja lógica de un repartidor.

Además de los escenarios de la historia se cubre lo que hace el navegador
real y el cliente de tests no: la petición llega proxificada (Vercel → Render,
Vite → Django), así que el ``Host`` que ve Django es el del backend aunque el
navegador esté en otro dominio. Por eso las vistas del coordinador son
``@csrf_exempt`` y la protección real es la sesión.
"""

import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from core.models import Repartidor

MENSAJE_EXITO = "Repartidor dado de baja con éxito"
MENSAJE_YA_DE_BAJA = "El repartidor ya fue dado de baja"
MENSAJE_NO_ENCONTRADO = "Repartidor no encontrado"
MENSAJE_NO_AUTENTICADO = "No autenticado"

# Host del frontend tal como lo ve el navegador (distinto del backend).
ORIGEN_FRONT = "https://mi-front.vercel.app"


class BajaRepartidorTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.coordinador = User.objects.create_user(
            username="coord", password="clave-segura-123"
        )
        self.client.force_login(self.coordinador)

        self.repartidor = Repartidor.objects.create(
            nombre="Juan",
            apellido="Pérez",
            dni=12345678,
            telefono="1122334455",
            mail="juan@test.com",
            tipo_vehiculo=Repartidor.TipoVehiculo.MOTO,
            estado=Repartidor.Estado.ACTIVO,
            token="ABC123",
        )

    def _url_detalle(self):
        return f"/api/repartidores/{self.repartidor.id}/detalle-baja/"

    def _url_baja(self):
        return f"/api/repartidores/{self.repartidor.id}/baja/"

    # --- Escenarios de la HU ------------------------------------------------

    def test_obtener_datos_repartidor_para_confirmacion(self):
        res = self.client.get(self._url_detalle())
        self.assertEqual(res.status_code, 200)

        repartidor = res.json()["repartidor"]
        self.assertEqual(repartidor["dni"], 12345678)
        self.assertEqual(repartidor["nombre"], "Juan")
        self.assertEqual(repartidor["telefono"], "1122334455")
        self.assertEqual(repartidor["mail"], "juan@test.com")
        self.assertEqual(repartidor["tipo_vehiculo"], Repartidor.TipoVehiculo.MOTO)

    def test_detalle_no_expone_el_token(self):
        res = self.client.get(self._url_detalle())
        self.assertNotIn("token", res.json()["repartidor"])

    def test_baja_repartidor_exitosa_y_bloquea_login(self):
        res = self.client.post(self._url_baja())
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["mensaje"], MENSAJE_EXITO)
        self.assertEqual(
            res.json()["repartidor"]["estado"], Repartidor.Estado.BAJA
        )

        self.repartidor.refresh_from_db()
        self.assertEqual(self.repartidor.estado, Repartidor.Estado.BAJA)

        login_res = self.client.post(
            "/api/login-repartidor/",
            data={"token": self.repartidor.token},
            content_type="application/json",
        )
        self.assertIn(login_res.status_code, [401, 403])

    def test_baja_repartidor_ya_dado_de_baja_devuelve_400(self):
        self.repartidor.estado = Repartidor.Estado.BAJA
        self.repartidor.save()
        res = self.client.post(self._url_baja())
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error"], MENSAJE_YA_DE_BAJA)

    def test_baja_repartidor_no_existente_devuelve_404(self):
        res = self.client.post("/api/repartidores/9999/baja/")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()["error"], MENSAJE_NO_ENCONTRADO)

    def test_metodo_no_permitido_devuelve_405(self):
        res = self.client.get(self._url_baja())
        self.assertEqual(res.status_code, 405)

    def test_no_autenticado_devuelve_401(self):
        self.client.logout()
        res = self.client.post(self._url_baja())
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["error"], MENSAJE_NO_AUTENTICADO)

    # --- Detalles que protegen los datos ------------------------------------

    def test_la_baja_conserva_el_token(self):
        """Es una baja lógica: el token no se regenera."""
        token_original = self.repartidor.token
        self.client.post(self._url_baja())
        self.repartidor.refresh_from_db()
        self.assertEqual(self.repartidor.token, token_original)

    def test_la_baja_no_toca_los_demas_campos(self):
        antes = Repartidor.objects.values().get(pk=self.repartidor.pk)
        self.client.post(self._url_baja())
        despues = Repartidor.objects.values().get(pk=self.repartidor.pk)

        for campo, valor in antes.items():
            if campo != "estado":
                self.assertEqual(despues[campo], valor, f"cambió el campo {campo}")

    def test_detalle_de_un_repartidor_ya_dado_de_baja_devuelve_400(self):
        Repartidor.objects.filter(pk=self.repartidor.pk).update(
            estado=Repartidor.Estado.BAJA
        )
        res = self.client.get(self._url_detalle())
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error"], MENSAJE_YA_DE_BAJA)

    def test_detalle_no_autenticado_devuelve_401(self):
        self.client.logout()
        res = self.client.get(self._url_detalle())
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["error"], MENSAJE_NO_AUTENTICADO)


class BajaRepartidorProxificadoTests(TestCase):
    """La petición como la manda el navegador contra el despliegue real.

    ``Client(enforce_csrf_checks=True)`` no saltea la verificación CSRF y el
    ``Host`` es el del backend, mientras el ``Origin`` es el del frontend:
    exactamente lo que ocurre detrás del rewrite de Vercel. Si alguien saca
    los ``@csrf_exempt`` sin configurar ``CSRF_TRUSTED_ORIGINS``, estos tests
    fallan con 403.
    """

    def setUp(self):
        User = get_user_model()
        User.objects.create_user(username="coord", password="clave-segura-123")
        self.repartidor = Repartidor.objects.create(
            nombre="Ana",
            apellido="Paz",
            dni=30111222,
            telefono="2215550000",
            mail="ana@test.com",
            tipo_vehiculo=Repartidor.TipoVehiculo.AUTO,
            estado=Repartidor.Estado.ACTIVO,
            token="PAZ123",
        )
        self.client = Client(enforce_csrf_checks=True)

    def _login_como_el_front(self):
        """Login por la API, con el Origin del frontend (dominio distinto)."""
        res = self.client.post(
            "/api/login-coordinador/",
            data=json.dumps({"username": "coord", "password": "clave-segura-123"}),
            content_type="application/json",
            HTTP_ORIGIN=ORIGEN_FRONT,
        )
        self.assertEqual(res.status_code, 200)
        return res

    def test_el_login_deja_la_cookie_de_sesion(self):
        res = self._login_como_el_front()
        self.assertIn("sessionid", res.cookies)

    def test_baja_desde_el_front_desplegado(self):
        self._login_como_el_front()
        res = self.client.post(
            f"/api/repartidores/{self.repartidor.id}/baja/",
            content_type="application/json",
            HTTP_ORIGIN=ORIGEN_FRONT,
            HTTP_REFERER=f"{ORIGEN_FRONT}/repartidores",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["mensaje"], MENSAJE_EXITO)

        self.repartidor.refresh_from_db()
        self.assertEqual(self.repartidor.estado, Repartidor.Estado.BAJA)

    def test_detalle_desde_el_front_desplegado(self):
        self._login_como_el_front()
        res = self.client.get(
            f"/api/repartidores/{self.repartidor.id}/detalle-baja/",
            HTTP_ORIGIN=ORIGEN_FRONT,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["repartidor"]["nombre"], "Ana")

    def test_sin_sesion_no_hay_baja_aunque_sea_post_simple(self):
        """Un POST de otro sitio no lleva la cookie: la sesión es la defensa."""
        sin_sesion = Client(enforce_csrf_checks=True)
        res = sin_sesion.post(
            f"/api/repartidores/{self.repartidor.id}/baja/",
            content_type="application/json",
            HTTP_ORIGIN="https://sitio-malicioso.example",
        )
        self.assertEqual(res.status_code, 401)

        self.repartidor.refresh_from_db()
        self.assertEqual(self.repartidor.estado, Repartidor.Estado.ACTIVO)
