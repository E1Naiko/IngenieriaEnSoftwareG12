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
            estado=Paquete.Estado.PENDIENTE,
        )

    def _get(self, params=None):
        return self.client.get(self.url, params)

    def _post(self, payload, token="__default__"):
        """POST como lo hace Dashboardrepartidor.tsx: con el token del repartidor.

        El token es obligatorio desde que el POST valida quién pide el cambio
        (HU #38). Pasar ``token=None`` para simular una petición sin token.
        """
        cuerpo = dict(payload)
        if token == "__default__":
            cuerpo.setdefault("token", self.repartidor.token)
        elif token is not None:
            cuerpo["token"] = token
        return self.client.post(
            self.url,
            data=json.dumps(cuerpo),
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

class ActualizarPedidoValidacionTests(TestCase):
    """Validaciones del POST (revisión del PR #79): token y baja del repartidor.

    El backend no guarda sesión del repartidor: el único dato que dice quién
    pide el cambio es el ``token`` del cuerpo. Sin estas validaciones, un
    request directo podía cambiar el estado de cualquier paquete.
    """

    def setUp(self):
        self.url = reverse("cambiar-estado-pedido")

        self.comercio = Comercio.objects.create(
            nombre="Kiosco Central", telefono="221-555-0100",
            direccion="Calle 7 #123",
        )
        self.cliente = Cliente.objects.create(
            nombre="Juan", apellido="Pérez", telefono="221-555-0200",
            direccion="Calle 44 #999", dni=30111222,
        )
        self.repartidor = Repartidor.objects.create(
            nombre="Ana", apellido="Gómez", dni=20333444,
            telefono="221-555-0300", mail="ana@example.com",
        )
        self.otro = Repartidor.objects.create(
            nombre="Luis", apellido="Sosa", dni=20999888,
            telefono="221-555-0400", mail="luis@example.com",
        )
        self.paquete = Paquete.objects.create(
            comercio=self.comercio,
            cliente=self.cliente,
            repartidor=self.repartidor,
            fecha_origen=date(2026, 10, 1),
            fecha_destino=date(2026, 10, 2),
            estado=Paquete.Estado.ASIGNADO,
        )

    def _post(self, payload):
        return self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_sin_token_devuelve_400(self):
        r = self._post({"id": self.paquete.id, "estado": "en_camino"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["message"], "Falta el token")

        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.estado, Paquete.Estado.ASIGNADO)

    def test_token_inexistente_devuelve_401(self):
        r = self._post({"token": "ZZZZZZ", "id": self.paquete.id, "estado": "en_camino"})
        self.assertEqual(r.status_code, 401)

        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.estado, Paquete.Estado.ASIGNADO)

    def test_repartidor_dado_de_baja_no_puede_cambiar_estados(self):
        """Escenario central de la HU #38 visto desde el otro endpoint."""
        Repartidor.objects.filter(pk=self.repartidor.pk).update(
            estado=Repartidor.Estado.BAJA
        )

        r = self._post(
            {"token": self.repartidor.token, "id": self.paquete.id, "estado": "en_camino"}
        )
        self.assertEqual(r.status_code, 403)
        self.assertIn("no se encuentra habilitado", r.json()["message"])

        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.estado, Paquete.Estado.ASIGNADO)

    def test_la_baja_se_detecta_aunque_el_estado_este_en_mayusculas(self):
        Repartidor.objects.filter(pk=self.repartidor.pk).update(estado="BAJA")

        r = self._post(
            {"token": self.repartidor.token, "id": self.paquete.id, "estado": "en_camino"}
        )
        self.assertEqual(r.status_code, 403)

    def test_otro_repartidor_no_puede_cambiar_un_paquete_ajeno(self):
        r = self._post(
            {"token": self.otro.token, "id": self.paquete.id, "estado": "en_camino"}
        )
        self.assertEqual(r.status_code, 403)
        self.assertIn("no está asignado", r.json()["message"])

        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.estado, Paquete.Estado.ASIGNADO)

    def test_paquete_sin_repartidor_no_se_puede_cambiar(self):
        Paquete.objects.filter(pk=self.paquete.pk).update(repartidor=None)

        r = self._post(
            {"token": self.repartidor.token, "id": self.paquete.id, "estado": "en_camino"}
        )
        self.assertEqual(r.status_code, 403)

    def test_el_asignado_puede_avanzar_el_estado(self):
        for estado in ("en_camino", "entregado"):
            r = self._post(
                {"token": self.repartidor.token, "id": self.paquete.id, "estado": estado}
            )
            self.assertEqual(r.status_code, 200, r.content)
            self.paquete.refresh_from_db()
            self.assertEqual(self.paquete.estado, estado)

    def test_el_get_sigue_siendo_publico(self):
        """La pantalla de seguimiento (HU #14) no manda token y debe seguir andando."""
        r = self.client.get(self.url, {"cod_seguimiento": self.paquete.cod_seguimiento})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["paquetes"]), 1)
