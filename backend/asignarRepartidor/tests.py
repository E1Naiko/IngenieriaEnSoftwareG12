"""
Tests de asignación de repartidores (HU: según vehículo y disponibilidad).

Ejecutar::

    cd backend
    DATABASE_MODE=sqlite python manage.py test asignarRepartidor
"""

import json
from datetime import date

from django.test import TestCase
from django.urls import reverse

from core.models import Cliente, Comercio, Paquete, Repartidor


MSG_SIN_VEHICULO = "No hay repartidores disponibles con el vehículo requerido"


class AsignarRepartidorTestBase(TestCase):
    """Datos comunes: un comercio, un cliente y repartidores de cada vehículo."""

    def setUp(self):
        self.url = reverse("asignarRepartidor")
        self.comercio = Comercio.objects.create(
            nombre="Comercio Sur",
            telefono="2214440000",
            direccion="Calle 7 1234",
        )
        self.cliente = Cliente.objects.create(
            nombre="Ana",
            apellido="Pérez",
            telefono="2214441111",
            direccion="Calle 12 #34",
            dni=30111222,
        )
        self.moto = self._repartidor("Juan", "Gómez", 30000001, Repartidor.TipoVehiculo.MOTO)
        self.auto = self._repartidor("Luis", "Ruiz", 30000002, Repartidor.TipoVehiculo.AUTO)
        self.camioneta = self._repartidor("Mara", "Lopez", 30000003, Repartidor.TipoVehiculo.CAMIONETA)

    def _repartidor(self, nombre, apellido, dni, tipo, estado=Repartidor.Estado.ACTIVO):
        return Repartidor.objects.create(
            nombre=nombre,
            apellido=apellido,
            dni=dni,
            telefono="2215550000",
            mail=f"{nombre.lower()}@example.com",
            tipo_vehiculo=tipo,
            estado=estado,
        )

    def _paquete(self, tamanio=Paquete.Tamanio.CHICO, repartidor=None, estado=Paquete.Estado.PENDIENTE):
        return Paquete.objects.create(
            comercio=self.comercio,
            cliente=self.cliente,
            tamanio=tamanio,
            estado=estado,
            repartidor=repartidor,
            fecha_origen=date(2026, 10, 27),
            fecha_destino=date(2026, 10, 31),
        )

    def _ids(self, response):
        return [r["id"] for r in response.json()["repartidores"]]

    def _post(self, body):
        return self.client.post(
            self.url,
            data=json.dumps(body),
            content_type="application/json",
        )


class ListadoFiltradoPorVehiculoTests(AsignarRepartidorTestBase):
    """Escenario 1: solo disponibles con vehículo adecuado al tamaño del paquete."""

    def test_paquete_chico_ofrece_todos_los_vehiculos(self):
        paquete = self._paquete(Paquete.Tamanio.CHICO)

        response = self.client.get(self.url, {"paquete": paquete.id})

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(self._ids(response), [self.moto.id, self.auto.id, self.camioneta.id])

    def test_paquete_mediano_excluye_moto(self):
        paquete = self._paquete(Paquete.Tamanio.MEDIANO)

        response = self.client.get(self.url, {"paquete": paquete.id})

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.moto.id, self._ids(response))
        self.assertCountEqual(self._ids(response), [self.auto.id, self.camioneta.id])

    def test_paquete_grande_solo_ofrece_camioneta_o_camion(self):
        paquete = self._paquete(Paquete.Tamanio.GRANDE)
        camion = self._repartidor("Tomás", "Díaz", 30000004, Repartidor.TipoVehiculo.CAMION)

        response = self.client.get(self.url, {"paquete": paquete.id})

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(self._ids(response), [self.camioneta.id, camion.id])

    def test_excluye_repartidores_no_disponibles(self):
        inactivo = self._repartidor("Pablo", "Sosa", 30000005, Repartidor.TipoVehiculo.CAMIONETA,
                                    estado=Repartidor.Estado.INACTIVO)
        baja = self._repartidor("Eva", "Mora", 30000006, Repartidor.TipoVehiculo.CAMIONETA,
                                estado=Repartidor.Estado.BAJA)
        paquete = self._paquete(Paquete.Tamanio.GRANDE)

        response = self.client.get(self.url, {"paquete": paquete.id})

        ids = self._ids(response)
        self.assertNotIn(inactivo.id, ids)
        self.assertNotIn(baja.id, ids)
        self.assertEqual(ids, [self.camioneta.id])

    def test_acepta_estado_disponible_de_la_base_actual(self):
        disponible = self._repartidor("Nora", "Kim", 30000007, Repartidor.TipoVehiculo.AUTO,
                                      estado=" disponible ")
        paquete = self._paquete(Paquete.Tamanio.MEDIANO)

        response = self.client.get(self.url, {"paquete": paquete.id})

        self.assertIn(disponible.id, self._ids(response))

    def test_escenario_2_sin_vehiculo_adecuado_muestra_mensaje(self):
        """Escenario 2: no hay camiones disponibles para un paquete grande."""
        # Solo hay moto y auto disponibles: ninguno alcanza el tamaño grande.
        self.camioneta.estado = Repartidor.Estado.INACTIVO
        self.camioneta.save()
        self.auto.delete()
        paquete = self._paquete(Paquete.Tamanio.GRANDE)

        response = self.client.get(self.url, {"paquete": paquete.id})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["mensaje"], MSG_SIN_VEHICULO)
        self.assertEqual(data["repartidores"], [])

    def test_escenario_2_el_paquete_queda_pendiente_sin_asignar(self):
        self.camioneta.estado = Repartidor.Estado.INACTIVO
        self.camioneta.save()
        paquete = self._paquete(Paquete.Tamanio.GRANDE)

        self.client.get(self.url, {"paquete": paquete.id})

        paquete.refresh_from_db()
        self.assertIsNone(paquete.repartidor)
        self.assertEqual(paquete.estado, Paquete.Estado.PENDIENTE)

    def test_paquete_inexistente_devuelve_400(self):
        response = self.client.get(self.url, {"paquete": 99999})

        self.assertEqual(response.status_code, 400)
        self.assertIn("paquete", response.json())

    def test_paquete_vacio_devuelve_400(self):
        response = self.client.get(self.url, {"paquete": ""})

        self.assertEqual(response.status_code, 400)
        self.assertIn("paquete", response.json())

    def test_sin_parametro_lista_todos_los_disponibles(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(self._ids(response), [self.moto.id, self.auto.id, self.camioneta.id])

    def test_rechaza_metodos_no_permitidos(self):
        response = self.client.put(self.url, data={})

        self.assertEqual(response.status_code, 405)


class AsignacionTests(AsignarRepartidorTestBase):
    """Asignación directa por el coordinador (POST)."""

    def test_asignacion_exitosa_no_cambia_el_estado_del_paquete(self):
        paquete = self._paquete(Paquete.Tamanio.MEDIANO)

        response = self._post({"paquete": paquete.id, "repartidor": self.auto.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["repartidor"], self.auto.id)
        paquete.refresh_from_db()
        self.assertEqual(paquete.repartidor_id, self.auto.id)
        # La actualización del estado pasa al repartidor: el coordinador no la toca.
        self.assertEqual(paquete.estado, Paquete.Estado.PENDIENTE)

    def test_asignacion_aparece_en_listado_del_repartidor(self):
        paquete = self._paquete(Paquete.Tamanio.CHICO)

        self._post({"paquete": paquete.id, "repartidor": self.moto.id})

        self.assertEqual(self.moto.listado_id_pedidos_asignados, [paquete.id])

    def test_no_permite_asignar_vehiculo_insuficiente(self):
        paquete = self._paquete(Paquete.Tamanio.GRANDE)

        response = self._post({"paquete": paquete.id, "repartidor": self.moto.id})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["repartidor"], MSG_SIN_VEHICULO)
        paquete.refresh_from_db()
        self.assertIsNone(paquete.repartidor)

    def test_no_permite_asignar_repartidor_no_disponible(self):
        inactivo = self._repartidor("Pablo", "Sosa", 30000008, Repartidor.TipoVehiculo.CAMIONETA,
                                    estado=Repartidor.Estado.INACTIVO)
        paquete = self._paquete(Paquete.Tamanio.CHICO)

        response = self._post({"paquete": paquete.id, "repartidor": inactivo.id})

        self.assertEqual(response.status_code, 400)
        paquete.refresh_from_db()
        self.assertIsNone(paquete.repartidor)

    def test_no_reasigna_un_paquete_ya_asignado(self):
        paquete = self._paquete(Paquete.Tamanio.CHICO, repartidor=self.moto)

        response = self._post({"paquete": paquete.id, "repartidor": self.camioneta.id})

        self.assertEqual(response.status_code, 409)
        paquete.refresh_from_db()
        self.assertEqual(paquete.repartidor_id, self.moto.id)

    def test_no_asigna_paquetes_entregados_o_cancelados(self):
        for estado in (Paquete.Estado.ENTREGADO, Paquete.Estado.CANCELADO):
            with self.subTest(estado=estado):
                paquete = self._paquete(Paquete.Tamanio.CHICO, estado=estado)

                response = self._post({"paquete": paquete.id, "repartidor": self.moto.id})

                self.assertEqual(response.status_code, 409)
                paquete.refresh_from_db()
                self.assertIsNone(paquete.repartidor)

    def test_campos_obligatorios(self):
        response = self._post({"paquete": "", "repartidor": None})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {
            "paquete": "Campo obligatorio *",
            "repartidor": "Campo obligatorio *",
        })

    def test_paquete_o_repartidor_inexistentes_devuelven_404(self):
        paquete = self._paquete()

        self.assertEqual(self._post({"paquete": 99999, "repartidor": self.moto.id}).status_code, 404)
        self.assertEqual(self._post({"paquete": paquete.id, "repartidor": 99999}).status_code, 404)
        self.assertEqual(self._post({"paquete": "abc", "repartidor": self.moto.id}).status_code, 404)

    def test_cuerpo_invalido_devuelve_400(self):
        response = self.client.post(self.url, data="no es json", content_type="application/json")

        self.assertEqual(response.status_code, 400)
