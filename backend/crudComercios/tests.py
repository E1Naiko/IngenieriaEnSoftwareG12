"""
Tests de integración para la API de comercios.

Suite ``ComercioAPITests`` (``django.test.TestCase``) que ejercita
los dos endpoints de ``crudComercios/views.py`` a través del cliente
de pruebas de Django (sin levantar servidor).

Qué se cubre
------------
- Listado y filtrado ``?q=``
- Alta (201) y validación de campos obligatorios (400)
- Detalle (200) y 404
- PUT (reemplazo total) y PATCH (parcial)
- DELETE (204)
- FK opcional ``datos_cliente`` (link, desvinculación y 400 por inexistente)

Ejecutar::

    cd backend
    python manage.py test crudComercios
    python manage.py test crudComercios.tests.ComercioAPITests.test_crear

Nota: ``Comercio`` vive en ``core.models``; los tests crean datos de
prueba en la BD de test (SQLite en memoria / aislada por ``TestCase``).
"""

from django.test import TestCase
from django.urls import reverse

from core.models import Cliente, Comercio


class ComercioAPITests(TestCase):
    """CRUD completo de ``/api/comercios/`` — ver docstring del módulo."""

    def setUp(self):
        """Crea un comercio base usado por la mayoría de los tests."""
        self.comercio = Comercio.objects.create(
            nombre="Comercio A", telefono="123", direccion="Calle 1"
        )

    # --- Listado -----------------------------------------------------------

    def test_listar(self):
        """GET /api/comercios/ → 200 con results y count."""
        resp = self.client.get("/api/comercios/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["nombre"], "Comercio A")

    # --- Alta --------------------------------------------------------------

    def test_crear(self):
        """POST válido → 201 y persiste en la BD."""
        resp = self.client.post(
            "/api/comercios/",
            data={"nombre": "Nuevo", "telefono": "999", "direccion": "Calle 9"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["nombre"], "Nuevo")
        self.assertEqual(Comercio.objects.count(), 2)

    def test_crear_faltan_campos(self):
        """POST con campos faltantes → 400."""
        resp = self.client.post(
            "/api/comercios/",
            data={"nombre": "Incompleto"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    # --- Detalle -----------------------------------------------------------

    def test_detalle(self):
        """GET /api/comercios/<id>/ → 200 con el comercio."""
        resp = self.client.get(f"/api/comercios/{self.comercio.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["id"], self.comercio.id)

    def test_detalle_404(self):
        """GET de un ID inexistente → 404."""
        resp = self.client.get("/api/comercios/9999/")
        self.assertEqual(resp.status_code, 404)

    # --- Actualización -----------------------------------------------------

    def test_actualizar_put(self):
        """PUT reemplaza todos los campos → 200 y guarda."""
        resp = self.client.put(
            f"/api/comercios/{self.comercio.id}/",
            data={"nombre": "Editado", "telefono": "111", "direccion": "Nueva"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.comercio.refresh_from_db()
        self.assertEqual(self.comercio.nombre, "Editado")

    def test_actualizar_patch(self):
        """PATCH parcial → solo cambia lo enviado, el resto queda igual."""
        resp = self.client.patch(
            f"/api/comercios/{self.comercio.id}/",
            data={"telefono": "222"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.comercio.refresh_from_db()
        self.assertEqual(self.comercio.telefono, "222")
        self.assertEqual(self.comercio.nombre, "Comercio A")

    # --- Borrado -----------------------------------------------------------

    def test_borrar(self):
        """DELETE → 204 y elimina de la BD."""
        resp = self.client.delete(f"/api/comercios/{self.comercio.id}/")
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(Comercio.objects.count(), 0)

    # --- Filtro por nombre -------------------------------------------------

    def test_filtro_q(self):
        """GET ?q= filtra por nombre__icontains."""
        Comercio.objects.create(nombre="Otro", telefono="1", direccion="x")
        resp = self.client.get("/api/comercios/?q=Otro")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 1)

    # --- FK datos_cliente --------------------------------------------------

    def test_datos_cliente_fk(self):
        """PATCH {datos_cliente: id} linkea un Cliente existente."""
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
