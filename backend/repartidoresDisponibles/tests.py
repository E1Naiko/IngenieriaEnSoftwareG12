import json

from django.test import TestCase
from django.urls import reverse

from core.models import Cliente, Comercio, Paquete, Repartidor


class DashboardRepartidoresTests(TestCase):
    """
    Tests para el endpoint que lista los repartidores activos.
    """

    def setUp(self):
        """
        Se ejecuta antes de cada test.

        Crea un repartidor activo y otro inactivo para comprobar
        que el endpoint filtre correctamente por estado.
        """
        self.url = reverse("dashboard_repartidores")

        self.repartidor_activo = Repartidor.objects.create(
            nombre="Juan",
            apellido="García",
            dni=12345678,
            telefono="2215551234",
            mail="juan@example.com",
            tipo_vehiculo=Repartidor.TipoVehiculo.MOTO,
            estado=Repartidor.Estado.ACTIVO,
        )

        self.repartidor_inactivo = Repartidor.objects.create(
            nombre="María",
            apellido="López",
            dni=23456789,
            telefono="2215555678",
            mail="maria@example.com",
            tipo_vehiculo=Repartidor.TipoVehiculo.AUTO,
            estado=Repartidor.Estado.INACTIVO,
        )

    def test_devuelve_solo_repartidores_activos(self):
        """
        Comprueba que la respuesta incluya al repartidor activo
        y excluya al que está inactivo.
        """
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        repartidores = data["repartidores"]

        # Debe devolver exactamente un repartidor.
        self.assertEqual(len(repartidores), 1)

        # El repartidor devuelto debe ser el activo.
        self.assertEqual(
            repartidores[0]["id"],
            self.repartidor_activo.id,
        )

        # Ningún repartidor inactivo debe aparecer en la respuesta.
        ids = [r["id"] for r in repartidores]
        self.assertNotIn(self.repartidor_inactivo.id, ids)

    def test_respuesta_contiene_los_campos_esperados(self):
        """
        Comprueba que cada repartidor tenga los campos
        definidos en el contrato JSON de la API.
        """
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        repartidor = response.json()["repartidores"][0]

        campos_esperados = {
            "id",
            "nombre",
            "apellido",
            "dni",
            "telefono",
            "mail",
            "tipo_vehiculo",
            "estado",
            "listado_id_pedidos_asignados",
        }

        self.assertEqual(set(repartidor.keys()), campos_esperados)

        self.assertEqual(repartidor["nombre"], "Juan")
        self.assertEqual(repartidor["apellido"], "García")
        self.assertEqual(repartidor["estado"], "activo")

    def test_devuelve_lista_vacia_si_no_hay_activos(self):
        """
        Comprueba el comportamiento cuando no hay repartidores
        activos en la base de datos.
        """
        # Desactivamos el único repartidor activo creado en setUp.
        self.repartidor_activo.estado = Repartidor.Estado.INACTIVO
        self.repartidor_activo.save()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data["repartidores"], [])
        self.assertIn("mensaje", data)

    def test_rechaza_metodos_distintos_de_get(self):
        """
        Comprueba que el endpoint rechace las peticiones POST.
        """
        response = self.client.post(self.url, data={})

        self.assertEqual(response.status_code, 405)

        data = response.json()
        self.assertEqual(data["error"], "Método no permitido.")

    def test_incluye_ids_de_paquetes_asignados(self):
        """
        Comprueba que listado_id_pedidos_asignados devuelva los IDs
        de los paquetes vinculados al repartidor activo.
        """
        comercio = Comercio.objects.create(
            nombre="Comercio Norte",
            telefono="2214440000",
            direccion="Calle 7 1234",
        )
        cliente = Cliente.objects.create(
            telefono="2214441111",
            direccion="Calle 50 567",
            dni=34567890,
            comercio=comercio,
        )
        paquete = Paquete.objects.create(
            repartidor=self.repartidor_activo,
            comercio=comercio,
            cliente=cliente,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        repartidor = response.json()["repartidores"][0]
        self.assertEqual(
            repartidor["listado_id_pedidos_asignados"],
            [paquete.id],
        )