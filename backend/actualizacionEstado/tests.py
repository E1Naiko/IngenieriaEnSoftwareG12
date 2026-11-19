"""Tests de la app actualizarPedido: cambiar estado de paquetes/pedidos."""

import json
from datetime import date
from django.test import TestCase
from django.urls import reverse
from core.models import Paquete, Comercio, Cliente, Repartidor


class ActualizarPedidoTests(TestCase):
    def setUp(self):
        self.url = reverse("cambiar-estado-pedido")

        # Crear datos necesarios para un paquete
        self.comercio = Comercio.objects.create(
            nombre="Kiosco Central",
            telefono="221-555-0100",
            direccion="Calle 7 #123"
        )
        self.cliente = Cliente.objects.create(
            telefono="221-555-0200",
            direccion="Calle 44 #999",
            dni=30111222
        )
        self.repartidor = Repartidor.objects.create(
            nombre="Ana",
            apellido="Gómez",
            dni=20333444,
            telefono="221-555-0300",
            mail="ana@example.com"
        )

        self.paquete = Paquete.objects.create(
            comercio=self.comercio,
            cliente=self.cliente,
            repartidor=self.repartidor,
            fecha_origen=date(2026, 10, 1),
            fecha_destino=date(2026, 10, 2),
            estado=Paquete.Estado.ASIGNADO,
        )

    def _get(self, params=None):
        return self.client.get(self.url, params)

    def _post(self, payload):
        return self.client.post(
            self.url,
            data=json.dumps({"token": self.repartidor.token, **payload}),
            content_type="application/json",
        )

    # --- Tests para GET ---
    def test_get_lista_paquetes_existentes(self):
        r = self._get()
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["message"], "Paquetes obtenidos correctamente.")
        self.assertEqual(len(data["paquetes"]), 1)
        self.assertEqual(data["paquetes"][0]["id"], self.paquete.id)
        self.assertEqual(data["paquetes"][0]["nombre_repartidor"], "Ana Gómez")

    def test_get_paquete_sin_repartidor_devuelve_nombre_null(self):
        self.paquete.repartidor = None
        self.paquete.save()

        r = self._get()

        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.json()["paquetes"][0]["nombre_repartidor"])

    def test_get_filtrar_por_cod_seguimiento(self):
        r = self._get({"cod_seguimiento": self.paquete.cod_seguimiento})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(len(data["paquetes"]), 1)
        self.assertEqual(data["paquetes"][0]["cod_seguimiento"], self.paquete.cod_seguimiento)

    def test_get_sin_paquetes(self):
        Paquete.objects.all().delete()
        r = self._get()
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["message"], "No hay paquetes registrados.")
        self.assertEqual(data["paquetes"], [])

    # --- Tests para POST ---
    def test_post_cambiar_estado_a_en_camino(self):
        r = self._post({"id": self.paquete.id, "estado": "en_camino"})
        self.assertEqual(r.status_code, 200)
        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.estado, "en_camino")
        self.assertEqual(r.json()["message"], "Estado del paquete actualizado correctamente.")

    def test_post_cambiar_estado_a_entregado(self):
        Paquete.objects.filter(pk=self.paquete.pk).update(estado=Paquete.Estado.EN_CAMINO)
        r = self._post({"id": self.paquete.id, "estado": "entregado"})
        self.assertEqual(r.status_code, 200)
        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.estado, "entregado")

    def test_post_no_modificar_paquete_entregado(self):
        # Primero lo entregamos
        self.paquete.estado = Paquete.Estado.ENTREGADO
        self.paquete.save()

        # Intentamos cambiarlo a otro estado
        r = self._post({"id": self.paquete.id, "estado": "pendiente"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("No se puede modificar", r.json()["message"])

    def test_post_no_modificar_paquete_cancelado(self):
        self.paquete.estado = Paquete.Estado.CANCELADO
        self.paquete.save()

        r = self._post({"id": self.paquete.id, "estado": "pendiente"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("No se puede modificar", r.json()["message"])

    def test_post_paquete_no_existe(self):
        r = self._post({"id": 99999, "estado": "en_camino"})
        self.assertEqual(r.status_code, 404)
        self.assertIn("No se encontró un paquete", r.json()["message"])

    def test_post_falta_id(self):
        r = self._post({"estado": "en_camino"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("Falta el campo 'id'", r.json()["message"])

    def test_post_falta_estado(self):
        r = self._post({"id": self.paquete.id})
        self.assertEqual(r.status_code, 400)
        self.assertIn("Falta el campo 'estado'", r.json()["message"])

    def test_post_estado_invalido(self):
        r = self._post({"id": self.paquete.id, "estado": "desconocido"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("Estado inválido", r.json()["message"])

    def test_post_json_invalido(self):
        r = self.client.post(
            self.url,
            data="no es json",
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("JSON válido", r.json()["message"])
    # --- Cancelación desde el panel del repartidor ---
    def test_cancelar_sin_causa_indica_el_campo_que_falta(self):
        """El front pide causa; si falta, responde 400 señalando ``causa``."""
        r = self._post({"id": self.paquete.id, "estado": "cancelado", "motivo": "Se rompió"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("causa de cancelación", r.json()["message"])
        self.assertEqual(r.json()["campo"], "causa")
        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.estado, Paquete.Estado.ASIGNADO)

    def test_cancelar_por_fuerza_mayor_libera_el_pedido(self):
        r = self._post({
            "id": self.paquete.id, "estado": "cancelado", "motivo": "  Se pinchó la rueda ",
            "causa": "fuerza_mayor", "ubicacion": {"latitud": -34.92, "longitud": -57.95},
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["message"], "El pedido se publicó en Pedidos cercanos.")
        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.estado, Paquete.Estado.PENDIENTE_REASIGNACION)
        self.assertIsNone(self.paquete.repartidor_id)
        self.assertEqual(self.paquete.motivo_cancelacion, "Se pinchó la rueda")

    def test_cancelar_por_ausencia_deja_el_paquete_en_devolucion(self):
        r = self._post({
            "id": self.paquete.id, "estado": "cancelado", "motivo": "No estaba",
            "causa": "cliente_ausente",
        })
        self.assertEqual(r.status_code, 200)
        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.estado, Paquete.Estado.EN_DEVOLUCION)

        # Segundo paso: confirmar la devolución, sin causa ni motivo.
        r = self._post({"id": self.paquete.id, "estado": "cancelado"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["message"], "Devolución al comercio confirmada.")
        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.estado, Paquete.Estado.CANCELADO)

    def test_motivo_invalido_indica_el_campo(self):
        r = self._post({
            "id": self.paquete.id, "estado": "cancelado", "causa": "fuerza_mayor", "motivo": "   ",
        })
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["campo"], "motivo")

    def test_estado_retirado_avanza_a_en_camino(self):
        Paquete.objects.filter(pk=self.paquete.pk).update(estado=Paquete.Estado.RETIRADO)
        r = self._post({"id": self.paquete.id, "estado": "en_camino"})
        self.assertEqual(r.status_code, 200)
        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.estado, Paquete.Estado.EN_CAMINO)
