from django.test import TestCase
from core.models import Repartidor


class BajaRepartidorTests(TestCase):
    def setUp(self):
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
        res = self.client.get(f"/api/repartidores/{self.repartidor.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["repartidor"]["dni"], 12345678)

    def test_baja_repartidor_exitosa(self):
        res = self.client.post(f"/api/repartidores/{self.repartidor.id}/baja/")
        self.assertEqual(res.status_code, 200)
        self.repartidor.refresh_from_db()
        self.assertEqual(self.repartidor.estado, Repartidor.Estado.BAJA)

    def test_baja_repartidor_ya_dado_de_baja_devuelve_400(self):
        self.repartidor.estado = Repartidor.Estado.BAJA
        self.repartidor.save()
        res = self.client.post(f"/api/repartidores/{self.repartidor.id}/baja/")
        self.assertEqual(res.status_code, 400)

    def test_baja_repartidor_no_existente_devuelve_404(self):
        res = self.client.post("/api/repartidores/9999/baja/")
        self.assertEqual(res.status_code, 404)