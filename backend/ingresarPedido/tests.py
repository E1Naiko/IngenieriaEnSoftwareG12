"""
Tests de la HU #37 (ingresar pedido) y del alta/listado de clientes.

Ejecutar::

    cd backend
    python manage.py test ingresarPedido
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from core.models import Cliente, Comercio, Paquete


class PedidoAPITests(TestCase):
    """``/api/pedidos/``: un test por escenario de la HU y sus bordes."""

    def setUp(self):
        self.comercio = Comercio.objects.create(nombre="Kiosco", telefono="1", direccion="Calle 1")
        self.cliente = Cliente.objects.create(telefono="2", direccion="Calle 2", dni=30111222)
        self.hoy = timezone.localdate()
        self.manana = self.hoy + timedelta(days=1)

    def _post(self, **cambios):
        """POST de un pedido válido, con los campos que se quieran pisar."""
        data = {
            "comercio": self.comercio.id,
            "cliente": self.cliente.id,
            "tamanio": "chico",
            "fecha_destino": self.manana.isoformat(),
            **cambios,
        }
        return self.client.post("/api/pedidos/", data=data, content_type="application/json")

    # --- Escenario 1 --------------------------------------------------------

    def test_crear(self):
        resp = self._post()
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["estado"], "pendiente")
        self.assertEqual(body["fecha_origen"], self.hoy.isoformat())
        self.assertTrue(body["cod_seguimiento"].startswith("SRFR-"))
        self.assertEqual(Paquete.objects.count(), 1)

    def test_listar(self):
        self._post()
        resp = self.client.get("/api/pedidos/")
        self.assertEqual(resp.json()["count"], 1)

    # --- Escenario 2 --------------------------------------------------------

    def test_campos_vacios(self):
        resp = self.client.post(
            "/api/pedidos/", data={"tamanio": ""}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json(),
            {c: "Campo obligatorio *" for c in ("comercio", "cliente", "tamanio", "fecha_destino")},
        )

    def test_fk_y_tamanio_invalidos(self):
        self.assertEqual(self._post(comercio=999).status_code, 400)
        self.assertEqual(self._post(cliente="abc").status_code, 400)
        self.assertEqual(self._post(tamanio="pequeño").status_code, 400)

    # --- Escenario 3 --------------------------------------------------------

    def test_fecha_invalida(self):
        ayer = (self.hoy - timedelta(days=1)).isoformat()
        for resp, campo in (
            (self._post(fecha_destino=ayer), "fecha_destino"),
            (self._post(fecha_destino="30/10/2026"), "fecha_destino"),
            (self._post(fecha_origen=(self.manana + timedelta(days=1)).isoformat()), "fecha_origen"),
        ):
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(resp.json(), {campo: "Fecha invalida"})

    def test_fecha_destino_hoy_es_valida(self):
        self.assertEqual(self._post(fecha_destino=self.hoy.isoformat()).status_code, 201)

    # --- Escenario 4 --------------------------------------------------------

    def test_duplicado(self):
        primero = self._post().json()
        resp = self._post(tamanio="grande")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["similar"]["id"], primero["id"])
        self.assertEqual(Paquete.objects.count(), 1)

    def test_duplicado_forzado(self):
        self._post()
        self.assertEqual(self._post(forzar=True).status_code, 201)
        self.assertEqual(Paquete.objects.count(), 2)

    def test_similar_cancelado_no_cuenta(self):
        self._post()
        Paquete.objects.update(estado=Paquete.Estado.CANCELADO)
        self.assertEqual(self._post().status_code, 201)

    def test_duplicado_con_estados_de_la_base_dev(self):
        """Los datos de dev usan mayúsculas y "ASIGNADO" (ver shortcut en views)."""
        self._post()
        for estado in (" PENDIENTE", "ASIGNADO", "EN_CAMINO"):
            Paquete.objects.update(estado=estado)
            self.assertEqual(self._post().status_code, 409)
        Paquete.objects.update(estado="ENTREGADO")
        self.assertEqual(self._post().status_code, 201)


class ClienteAPITests(TestCase):
    """``/api/clientes/``: lo mínimo para el selector y el popup del front."""

    def _post(self, **data):
        return self.client.post("/api/clientes/", data=data, content_type="application/json")

    def test_crear_y_listar(self):
        resp = self._post(telefono="221", direccion="Calle 7", dni=40123456)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["dni"], 40123456)
        self.assertEqual(self.client.get("/api/clientes/").json()["count"], 1)

    def test_validaciones(self):
        self.assertEqual(self._post(telefono="221").status_code, 400)
        self.assertEqual(self._post(telefono="1", direccion="x", dni="12a").status_code, 400)
        self._post(telefono="1", direccion="x", dni="123")
        resp = self._post(telefono="2", direccion="y", dni=123)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("dni", resp.json())
