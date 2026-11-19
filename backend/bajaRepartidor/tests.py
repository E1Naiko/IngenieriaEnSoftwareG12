from django.contrib.auth import get_user_model
from django.test import TestCase
from core.models import Repartidor


class BajaRepartidorTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.coordinador = User.objects.create_user(username="coord", password="123")
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

    def test_obtener_datos_repartidor_para_confirmacion(self):
        res = self.client.get(f"/api/repartidores/{self.repartidor.id}/detalle-baja/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["repartidor"]["dni"], 12345678)

    def test_baja_repartidor_exitosa_y_bloquea_login(self):
        res = self.client.post(f"/api/repartidores/{self.repartidor.id}/baja/")
        self.assertEqual(res.status_code, 200)
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
        res = self.client.post(f"/api/repartidores/{self.repartidor.id}/baja/")
        self.assertEqual(res.status_code, 400)

    def test_baja_repartidor_no_existente_devuelve_404(self):
        res = self.client.post("/api/repartidores/9999/baja/")
        self.assertEqual(res.status_code, 404)

    def test_metodo_no_permitido_devuelve_405(self):
        res = self.client.get(f"/api/repartidores/{self.repartidor.id}/baja/")
        self.assertEqual(res.status_code, 405)

    def test_no_autenticado_devuelve_401(self):
        self.client.logout()
        res = self.client.post(f"/api/repartidores/{self.repartidor.id}/baja/")
        self.assertEqual(res.status_code, 401)