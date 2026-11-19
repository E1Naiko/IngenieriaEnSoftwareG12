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

    def _post(self, payload):
        return self.client.post(
            self.url,
            data=json.dumps(payload),
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

    def test_post_cambiar_estado_a_entregado_con_dni_correcto(self):
        r = self._post(
            {"id": self.paquete.id, "estado": "entregado", "dni_receptor": 30111222}
        )
        self.assertEqual(r.status_code, 200)
        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.estado, "entregado")
        self.assertEqual(r.json()["message"], "Entrega validada con el DNI del receptor.")

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

class ValidarEntregaConDNITests(TestCase):
    """HU #23 — Validar la entrega con el número del DNI del receptor.

    La regla de la historia es *comprobar* el DNI del cliente, no solo
    adjuntarlo: si no coincide, el paquete no pasa a entregado.
    """

    def setUp(self):
        self.url = reverse("cambiar-estado-pedido")
        self.comercio = Comercio.objects.create(
            nombre="Kiosco Central", telefono="221-555-0100", direccion="Calle 7 #123"
        )
        self.cliente = Cliente.objects.create(
            nombre="Ana", apellido="Gómez", telefono="221-555-0200",
            direccion="Calle 44 #999", dni=30111222,
        )
        self.repartidor = Repartidor.objects.create(
            nombre="Ana", apellido="Paz", dni=20333444,
            telefono="221-555-0300", mail="ana@example.com",
        )
        self.paquete = Paquete.objects.create(
            comercio=self.comercio, cliente=self.cliente, repartidor=self.repartidor,
            fecha_origen=date(2026, 10, 1), fecha_destino=date(2026, 10, 2),
            estado=Paquete.Estado.EN_CAMINO,
        )

    def _entregar(self, **extra):
        return self.client.post(
            self.url,
            data=json.dumps({"id": self.paquete.id, "estado": "entregado", **extra}),
            content_type="application/json",
        )

    def _estado(self):
        self.paquete.refresh_from_db()
        return self.paquete.estado

    # --- Escenario 1: validación exitosa ---------------------------------
    def test_dni_correcto_entrega_el_paquete(self):
        r = self._entregar(dni_receptor=30111222)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self._estado(), "entregado")

    def test_dni_correcto_como_texto_con_puntos_y_espacios(self):
        """El repartidor tipea como en el DNI: "30.111.222"."""
        r = self._entregar(dni_receptor=" 30.111.222 ")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self._estado(), "entregado")

    def test_acepta_el_campo_dni_ademas_de_dni_receptor(self):
        r = self._entregar(dni="30111222")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self._estado(), "entregado")

    # --- Escenario 2: sin comprobante ------------------------------------
    def test_sin_dni_no_entrega_y_muestra_el_mensaje_de_la_hu(self):
        r = self._entregar()
        self.assertEqual(r.status_code, 400)
        self.assertEqual(
            r.json()["message"],
            "Necesario el numero del DNI del cliente para finalizar la entrega",
        )
        # Lo importante: el paquete NO cambió de estado.
        self.assertEqual(self._estado(), "en_camino")

    def test_dni_vacio_o_sin_digitos_no_entrega(self):
        for valor in ("", "   ", ".", None, True):
            with self.subTest(valor=valor):
                self.paquete.estado = Paquete.Estado.EN_CAMINO
                self.paquete.save()
                r = self._entregar(dni_receptor=valor)
                self.assertEqual(r.status_code, 400)
                self.assertIn("Necesario el numero del DNI", r.json()["message"])
                self.assertEqual(self._estado(), "en_camino")

    # --- DNI que no coincide ---------------------------------------------
    def test_dni_incorrecto_no_entrega_e_informa_el_correcto(self):
        r = self._entregar(dni_receptor=11111111)
        self.assertEqual(r.status_code, 400)
        self.assertIn("no coincide", r.json()["message"])
        self.assertIn("30111222", r.json()["message"])
        self.assertEqual(self._estado(), "en_camino")

    def test_el_dni_de_otro_cliente_no_sirve(self):
        Cliente.objects.create(
            nombre="Otro", apellido="Cliente", telefono="1",
            direccion="Otra", dni=29999888,
        )
        r = self._entregar(dni_receptor=29999888)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self._estado(), "en_camino")

    # --- El DNI no se exige para los demás estados ------------------------
    def test_los_otros_estados_no_piden_dni(self):
        r = self.client.post(
            self.url,
            data=json.dumps({"id": self.paquete.id, "estado": "en_camino"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self._estado(), "en_camino")

    # --- Comprobante (foto) opcional -------------------------------------
    def test_la_foto_es_opcional(self):
        r = self._entregar(dni_receptor=30111222)
        self.assertEqual(r.status_code, 200)
        self.paquete.refresh_from_db()
        self.assertIsNone(self.paquete.comprobante)

    def test_guarda_el_comprobante_cuando_llega_la_foto(self):
        from core.models import Comprobante
        from django.core.files.uploadedfile import SimpleUploadedFile

        imagen = SimpleUploadedFile("dni.jpg", b"\xff\xd8\xff\xe0contenido", content_type="image/jpeg")
        import base64 as b64

        data_url = "data:image/jpeg;base64," + b64.b64encode(imagen.read()).decode()
        r = self._entregar(dni_receptor=30111222, foto_dni=data_url)
        self.assertEqual(r.status_code, 200)
        self.paquete.refresh_from_db()
        self.assertIsNotNone(self.paquete.comprobante)
        self.assertEqual(Comprobante.objects.count(), 1)
        self.assertTrue(self.paquete.comprobante.file.name.startswith("comprobantes/"))

    def test_foto_mal_formada_avisa_sin_descartarla_en_silencio(self):
        r = self._entregar(dni_receptor=30111222, foto_dni="data:image/jpeg;base64,@@@no-es-base64@@@")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self._estado(), "en_camino")

    def test_formato_de_foto_no_admitido(self):
        r = self._entregar(dni_receptor=30111222, foto_dni="data:application/pdf;base64,QUJD")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self._estado(), "en_camino")
