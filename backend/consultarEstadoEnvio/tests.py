"""Pruebas de la consulta del estado actual de un envío.

Ejecutar desde backend: python manage.py test consultarEstadoEnvio
"""

import json
from datetime import date

from django.test import Client as HttpClient
from django.test import TestCase
from django.urls import reverse

from core.models import Cliente, Comercio, Paquete


class ConsultarEstadoEnvioTests(TestCase):
    def setUp(self):
        self.url = reverse("consultar-estado-envio")
        self.comercio = Comercio.objects.create(
            nombre="Kiosco", telefono="2211111111", direccion="Calle 1"
        )
        self.cliente = Cliente.objects.create(
            nombre="Ana",
            apellido="Pérez",
            telefono="2212222222",
            direccion="Calle 2",
            dni=30111222,
        )
        otro_cliente = Cliente.objects.create(
            nombre="Luis",
            apellido="Gómez",
            telefono="2213333333",
            direccion="Calle 3",
            dni=30222333,
        )
        self.paquete = Paquete.objects.create(
            comercio=self.comercio,
            cliente=self.cliente,
            estado=Paquete.Estado.EN_CAMINO,
            fecha_origen=date(2026, 10, 1),
            fecha_destino=date(2026, 10, 2),
        )
        self.otro_paquete = Paquete.objects.create(
            comercio=self.comercio,
            cliente=otro_cliente,
            estado=Paquete.Estado.PENDIENTE,
            fecha_origen=date(2026, 10, 1),
            fecha_destino=date(2026, 10, 2),
        )

    def _post(self, datos):
        return self.client.post(
            self.url, data=json.dumps(datos), content_type="application/json"
        )

    def test_consulta_devuelve_solo_el_estado(self):
        respuesta = self._post({"cod_seguimiento": self.paquete.cod_seguimiento})

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"estado": "en_camino"})

    def test_cada_codigo_consulta_solamente_su_paquete(self):
        self.assertNotEqual(
            self.paquete.cod_seguimiento, self.otro_paquete.cod_seguimiento
        )
        primero = self._post({"cod_seguimiento": self.paquete.cod_seguimiento})
        segundo = self._post({"cod_seguimiento": self.otro_paquete.cod_seguimiento})

        self.assertEqual(primero.json(), {"estado": "en_camino"})
        self.assertEqual(segundo.json(), {"estado": "pendiente"})

    def test_admite_minusculas_y_espacios_alrededor_del_codigo(self):
        codigo = f"  {self.paquete.cod_seguimiento.lower()}  "
        respuesta = self._post({"cod_seguimiento": codigo})

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"estado": "en_camino"})

    def test_consulta_el_estado_actual_sin_modificar_el_paquete(self):
        self.paquete.estado = Paquete.Estado.ENTREGADO
        self.paquete.save(update_fields=["estado"])
        respuesta = self._post({"cod_seguimiento": self.paquete.cod_seguimiento})

        self.assertEqual(respuesta.json(), {"estado": "entregado"})
        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.estado, Paquete.Estado.ENTREGADO)
        self.assertEqual(Paquete.objects.count(), 2)

    def test_codigo_inexistente_no_devuelve_datos(self):
        respuesta = self._post({"cod_seguimiento": "SRFR-NOEXISTE"})

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(
            respuesta.json(),
            {"message": "No se encontró un envío con ese código de seguimiento."},
        )

    def test_un_codigo_no_puede_usarse_para_listar_otros_paquetes(self):
        respuesta = self._post({"cod_seguimiento": "SRFR-' OR 1=1 --"})

        self.assertEqual(respuesta.status_code, 404)
        self.assertNotIn("estado", respuesta.json())

    def test_codigo_faltante_o_invalido(self):
        casos = (
            {},
            {"id": self.paquete.id},
            {"cod_seguimiento": ""},
            {"cod_seguimiento": " \t "},
            {"cod_seguimiento": None},
            {"cod_seguimiento": 123},
            {"cod_seguimiento": [self.paquete.cod_seguimiento]},
            {"cod_seguimiento": "A" * 256},
            {"cod_seguimiento": "SRFR-\x00"},
            {"cod_seguimiento": "\ud800"},
        )
        for datos in casos:
            with self.subTest(datos=datos):
                respuesta = self._post(datos)
                self.assertEqual(respuesta.status_code, 400)
                self.assertEqual(
                    respuesta.json(),
                    {"message": "Ingresá un código de seguimiento válido."},
                )

    def test_cuerpo_json_invalido_o_que_no_es_un_objeto(self):
        for cuerpo in (b"{", b"\xff", b"[]", b"null", b'"texto"'):
            with self.subTest(cuerpo=cuerpo):
                respuesta = self.client.post(
                    self.url, data=cuerpo, content_type="application/json"
                )
                self.assertEqual(respuesta.status_code, 400)
                self.assertEqual(
                    respuesta.json(),
                    {"message": "El cuerpo debe ser un objeto JSON válido."},
                )

    def test_solo_acepta_post_y_no_lista_por_get(self):
        respuesta = self.client.get(
            self.url, {"cod_seguimiento": self.paquete.cod_seguimiento}
        )
        self.assertEqual(respuesta.status_code, 405)
        self.assertEqual(respuesta.headers["Allow"], "POST")

        for metodo in ("PUT", "PATCH", "DELETE"):
            with self.subTest(metodo=metodo):
                respuesta = self.client.generic(metodo, self.url)
                self.assertEqual(respuesta.status_code, 405)

    def test_consulta_publica_sin_sesion_ni_cookie_csrf(self):
        cliente_publico = HttpClient(enforce_csrf_checks=True)
        respuesta = cliente_publico.post(
            self.url,
            data=json.dumps({"cod_seguimiento": self.paquete.cod_seguimiento}),
            content_type="application/json",
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"estado": "en_camino"})

    def test_respuestas_no_se_guardan_en_cache(self):
        for codigo in (self.paquete.cod_seguimiento, "SRFR-NOEXISTE", ""):
            with self.subTest(codigo=codigo):
                respuesta = self._post({"cod_seguimiento": codigo})
                self.assertIn("no-store", respuesta.headers["Cache-Control"])
