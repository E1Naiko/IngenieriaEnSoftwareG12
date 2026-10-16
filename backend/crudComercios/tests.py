from django.test import TestCase
from django.urls import reverse

from core.models import Cliente, Comercio


class ComercioAPITests(TestCase):
    def setUp(self):
        self.comercio = Comercio.objects.create(
            nombre="Comercio A", telefono="123", direccion="Calle 1"
        )

    def test_listar(self):
        resp = self.client.get("/api/comercios/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["nombre"], "Comercio A")

    def test_crear(self):
        resp = self.client.post(
            "/api/comercios/",
            data={"nombre": "Nuevo", "telefono": "999", "direccion": "Calle 9"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["nombre"], "Nuevo")
        self.assertEqual(Comercio.objects.count(), 2)

    def test_crear_faltan_campos(self):
        resp = self.client.post(
            "/api/comercios/",
            data={"nombre": "Incompleto"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_detalle(self):
        resp = self.client.get(f"/api/comercios/{self.comercio.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["id"], self.comercio.id)

    def test_detalle_404(self):
        resp = self.client.get("/api/comercios/9999/")
        self.assertEqual(resp.status_code, 404)

    def test_actualizar_put(self):
        resp = self.client.put(
            f"/api/comercios/{self.comercio.id}/",
            data={"nombre": "Editado", "telefono": "111", "direccion": "Nueva"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.comercio.refresh_from_db()
        self.assertEqual(self.comercio.nombre, "Editado")

    def test_actualizar_patch(self):
        resp = self.client.patch(
            f"/api/comercios/{self.comercio.id}/",
            data={"telefono": "222"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.comercio.refresh_from_db()
        self.assertEqual(self.comercio.telefono, "222")
        self.assertEqual(self.comercio.nombre, "Comercio A")

    def test_borrar(self):
        resp = self.client.delete(f"/api/comercios/{self.comercio.id}/")
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(Comercio.objects.count(), 0)

    def test_filtro_q(self):
        Comercio.objects.create(nombre="Otro", telefono="1", direccion="x")
        resp = self.client.get("/api/comercios/?q=Otro")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 1)

    def test_datos_cliente_fk(self):
        cliente = Cliente.objects.create(
            telefono="1", direccion="d", dni=12345678, comercio=self.comercio
        )
        # link comercio -> cliente (ciclo)
        resp = self.client.patch(
            f"/api/comercios/{self.comercio.id}/",
            data={"datos_cliente": cliente.id},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["datos_cliente"], cliente.id)
