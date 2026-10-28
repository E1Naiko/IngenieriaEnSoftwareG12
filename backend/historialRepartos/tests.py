"""
Tests de la HU "Como coordinador quiero ver el historial de repartos".

Cubren un caso por escenario y las dos reglas de la historia:

- **Solo el coordinador puede ver el historial**: sin sesión la API responde
  ``401`` (también se prueba el flujo real: login del coordinador y después
  consulta).
- **Hay un historial por cada repartidor**: cada endpoint devuelve únicamente
  los paquetes de la FK ``paquete.repartidor`` del repartidor consultado.

Escenarios:

1. El coordinador presiona "historial" → ``GET /api/historial/`` (listado con
   el resumen de cada repartidor).
2. El coordinador selecciona un repartidor → ``GET /api/historial/<id>/``
   (historial completo de ese repartidor).

Ejecutar::

    cd backend
    DATABASE_MODE=sqlite python manage.py test historialRepartos
"""

from datetime import date

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from core.models import Cliente, Comercio, Comprobante, Paquete, Repartidor

from .views import (
    MSG_NO_HAY_REPARTIDORES,
    MSG_REPARTIDOR_NO_ENCONTRADO,
    MSG_SIN_ENTREGAS,
    MSG_SOLO_COORDINADOR,
)


class HistorialTestsBase(TestCase):
    """Datos comunes: un coordinador y repartidores con historias distintas."""

    @classmethod
    def setUpTestData(cls):
        cls.clave = "clave-segura-123"
        cls.coordinador = User.objects.create_user(
            username="coordinador", password=cls.clave
        )

        cls.comercio = Comercio.objects.create(
            nombre="Kiosco Central",
            telefono="221-555-0100",
            direccion="Calle 7 #123",
        )
        cls.cliente = Cliente.objects.create(
            nombre="Ana",
            apellido="Pérez",
            dni=30111222,
            telefono="221-555-0200",
            direccion="Calle 12 #34",
        )

        # Juan ya entregó dos pedidos; Ana (la repartidora) todavía no entregó
        # ninguno. Los DNI y las fechas son distintos para poder ordenar.
        cls.juan = Repartidor.objects.create(
            nombre="Juan",
            apellido="Gómez",
            dni=40111222,
            telefono="221-555-0300",
            mail="juan@example.com",
        )
        cls.ana = Repartidor.objects.create(
            nombre="Ana",
            apellido="López",
            dni=40222333,
            telefono="221-555-0400",
            mail="ana@example.com",
            tipo_vehiculo=Repartidor.TipoVehiculo.AUTO,
        )

        cls.entrega_vieja = cls._paquete(
            repartidor=cls.juan,
            estado=Paquete.Estado.ENTREGADO,
            fecha_destino=date(2026, 10, 10),
        )
        cls.entrega_nueva = cls._paquete(
            repartidor=cls.juan,
            estado=Paquete.Estado.ENTREGADO,
            fecha_destino=date(2026, 10, 25),
            tamanio=Paquete.Tamanio.GRANDE,
        )
        # Pedidos que NO son parte del historial: solo cuenta "entregado".
        cls.pendiente = cls._paquete(repartidor=cls.juan)
        cls.en_camino = cls._paquete(
            repartidor=cls.juan, estado=Paquete.Estado.EN_CAMINO
        )
        cls.retirado = cls._paquete(
            repartidor=cls.juan, estado=Paquete.Estado.RETIRADO
        )
        cls.cancelado = cls._paquete(
            repartidor=cls.juan, estado=Paquete.Estado.CANCELADO
        )
        # Pedido entregado de OTRO repartidor: no debe aparecer en el historial
        # de Juan (regla: un historial por cada repartidor).
        cls.entrega_de_ana = cls._paquete(
            repartidor=cls.ana,
            estado=Paquete.Estado.ENTREGADO,
            fecha_destino=date(2026, 10, 20),
        )

    @classmethod
    def _paquete(cls, **kwargs):
        """Crea un paquete del comercio/cliente base con los datos indicados."""
        datos = {
            "comercio": cls.comercio,
            "cliente": cls.cliente,
            "fecha_origen": date(2026, 10, 1),
            "fecha_destino": date(2026, 10, 2),
        }
        datos.update(kwargs)
        return Paquete.objects.create(**datos)

    def setUp(self):
        self.url_listado = reverse("historial-repartidores")
        self.client.force_login(self.coordinador)

    def url_historial(self, repartidor):
        return reverse("historial-repartidor", args=[repartidor.pk])


class ListadoDeRepartidoresTests(HistorialTestsBase):
    """Escenario 1: el coordinador presiona "historial"."""

    def test_listado_devuelve_200_con_el_resumen_de_cada_repartidor(self):
        resp = self.client.get(self.url_listado)

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(set(data), {"repartidores", "total_repartidores"})
        self.assertEqual(data["total_repartidores"], 2)

        por_id = {item["id"]: item for item in data["repartidores"]}
        self.assertEqual(set(por_id), {self.juan.id, self.ana.id})
        self.assertEqual(
            set(por_id[self.juan.id]),
            {
                "id",
                "nombre",
                "apellido",
                "dni",
                "telefono",
                "mail",
                "tipo_vehiculo",
                "estado",
                "entregas",
                "ultima_entrega",
            },
        )

    def test_listado_cuenta_las_entregas_y_la_ultima_fecha(self):
        """Solo suma paquetes ``entregado``; la fecha es la de la última entrega."""
        resp = self.client.get(self.url_listado)

        por_id = {item["id"]: item for item in resp.json()["repartidores"]}
        self.assertEqual(por_id[self.juan.id]["entregas"], 2)
        self.assertEqual(por_id[self.juan.id]["ultima_entrega"], "2026-10-25")
        self.assertEqual(por_id[self.ana.id]["entregas"], 1)
        self.assertEqual(por_id[self.ana.id]["ultima_entrega"], "2026-10-20")

    def test_listado_incluye_repartidores_sin_entregas(self):
        """Un repartidor nuevo tiene historial vacío, pero se puede elegir."""
        nuevo = Repartidor.objects.create(
            nombre="Bruno",
            apellido="Díaz",
            dni=40333444,
            telefono="221-555-0500",
            mail="bruno@example.com",
        )

        resp = self.client.get(self.url_listado)

        por_id = {item["id"]: item for item in resp.json()["repartidores"]}
        self.assertIn(nuevo.id, por_id)
        self.assertEqual(por_id[nuevo.id]["entregas"], 0)
        self.assertIsNone(por_id[nuevo.id]["ultima_entrega"])

    def test_listado_ordena_por_apellido_y_nombre(self):
        resp = self.client.get(self.url_listado)

        apellidos = [item["apellido"] for item in resp.json()["repartidores"]]
        self.assertEqual(apellidos, ["Gómez", "López"])

    def test_listado_normaliza_el_estado_en_mayusculas(self):
        """La columna es un varchar libre: la BD puede tener 'ACTIVO'."""
        Repartidor.objects.filter(pk=self.juan.pk).update(estado="ACTIVO")

        resp = self.client.get(self.url_listado)

        por_id = {item["id"]: item for item in resp.json()["repartidores"]}
        self.assertEqual(por_id[self.juan.id]["estado"], "activo")

    def test_sin_repartidores_devuelve_lista_vacia_y_mensaje(self):
        Repartidor.objects.all().delete()

        resp = self.client.get(self.url_listado)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {
                "mensaje": MSG_NO_HAY_REPARTIDORES,
                "repartidores": [],
                "total_repartidores": 0,
            },
        )

    def test_metodo_distinto_de_get_devuelve_405(self):
        """Con CSRF activado (como en el servidor real) el POST da 405, no 403."""
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.coordinador)
        resp = cliente.post(self.url_listado)

        self.assertEqual(resp.status_code, 405)


class HistorialDeUnRepartidorTests(HistorialTestsBase):
    """Escenario 2: el coordinador selecciona un repartidor."""

    def test_devuelve_200_con_el_contrato_del_historial(self):
        resp = self.client.get(self.url_historial(self.juan))

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(set(data), {"repartidor", "entregas", "total_entregas"})
        self.assertEqual(data["total_entregas"], 2)
        self.assertEqual(len(data["entregas"]), 2)
        self.assertEqual(
            set(data["entregas"][0]),
            {
                "id",
                "cod_seguimiento",
                "estado",
                "tamanio",
                "comercio",
                "destinatario",
                "direccion",
                "fecha_origen",
                "fecha_destino",
                "comprobante",
            },
        )

    def test_los_datos_del_repartidor_son_los_del_elegido(self):
        resp = self.client.get(self.url_historial(self.ana))

        repartidor = resp.json()["repartidor"]
        self.assertEqual(repartidor["id"], self.ana.id)
        self.assertEqual(repartidor["nombre"], "Ana")
        self.assertEqual(repartidor["apellido"], "López")
        self.assertEqual(repartidor["tipo_vehiculo"], "auto")

    def test_cada_repartidor_tiene_su_propio_historial(self):
        """Regla de la HU: hay un historial por cada repartidor, sin mezclarse."""
        resp_juan = self.client.get(self.url_historial(self.juan))
        resp_ana = self.client.get(self.url_historial(self.ana))

        ids_juan = {e["id"] for e in resp_juan.json()["entregas"]}
        ids_ana = {e["id"] for e in resp_ana.json()["entregas"]}
        self.assertEqual(ids_juan, {self.entrega_vieja.id, self.entrega_nueva.id})
        self.assertEqual(ids_ana, {self.entrega_de_ana.id})
        self.assertFalse(ids_juan & ids_ana)

    def test_no_incluye_paquetes_que_no_estan_entregados(self):
        resp = self.client.get(self.url_historial(self.juan))

        ids = {e["id"] for e in resp.json()["entregas"]}
        for paquete in (self.pendiente, self.en_camino, self.retirado, self.cancelado):
            with self.subTest(paquete=paquete.id, estado=paquete.estado):
                self.assertNotIn(paquete.id, ids)

    def test_entregado_en_mayusculas_tambien_es_historial(self):
        """La BD es varchar: un 'ENTREGADO' histórico cuenta como entregado."""
        Paquete.objects.filter(pk=self.entrega_vieja.pk).update(estado="ENTREGADO")

        resp = self.client.get(self.url_historial(self.juan))

        entregas = {e["id"]: e for e in resp.json()["entregas"]}
        self.assertEqual(set(entregas), {self.entrega_vieja.id, self.entrega_nueva.id})
        # El contrato devuelve el estado normalizado, como el del repartidor.
        self.assertEqual(entregas[self.entrega_vieja.id]["estado"], "entregado")

    def test_orden_del_mas_reciente_al_mas_viejo(self):
        resp = self.client.get(self.url_historial(self.juan))
        entregas = resp.json()["entregas"]

        self.assertEqual(
            [e["id"] for e in entregas],
            [self.entrega_nueva.id, self.entrega_vieja.id],
        )
        self.assertEqual(
            [e["fecha_destino"] for e in entregas], ["2026-10-25", "2026-10-10"]
        )

    def test_entrega_trae_los_datos_que_muestra_la_pantalla(self):
        resp = self.client.get(self.url_historial(self.juan))

        entrega = next(
            e for e in resp.json()["entregas"] if e["id"] == self.entrega_nueva.id
        )
        self.assertEqual(entrega["cod_seguimiento"], self.entrega_nueva.cod_seguimiento)
        self.assertEqual(entrega["estado"], Paquete.Estado.ENTREGADO)
        self.assertEqual(entrega["tamanio"], Paquete.Tamanio.GRANDE)
        self.assertEqual(entrega["comercio"], "Kiosco Central")
        self.assertEqual(entrega["destinatario"], "Ana Pérez")
        self.assertEqual(entrega["direccion"], "Calle 12 #34")
        self.assertIsNone(entrega["comprobante"])

    def test_comprobante_se_devuelve_como_url_relativa(self):
        comprobante = Comprobante.objects.create()
        comprobante.file.name = "comprobantes/2026/10/entrega.jpg"
        comprobante.save()
        Paquete.objects.filter(pk=self.entrega_nueva.pk).update(comprobante=comprobante)

        resp = self.client.get(self.url_historial(self.juan))

        entrega = next(
            e for e in resp.json()["entregas"] if e["id"] == self.entrega_nueva.id
        )
        self.assertEqual(
            entrega["comprobante"], "/media/comprobantes/2026/10/entrega.jpg"
        )

    def test_repartidor_sin_entregas_devuelve_historial_vacio_con_mensaje(self):
        self.ana.paquetes.all().delete()

        resp = self.client.get(self.url_historial(self.ana))

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(set(data), {"repartidor", "entregas", "total_entregas", "mensaje"})
        self.assertEqual(data["mensaje"], MSG_SIN_ENTREGAS)
        self.assertEqual(data["entregas"], [])
        self.assertEqual(data["total_entregas"], 0)

    def test_repartidor_inexistente_devuelve_404(self):
        resp = self.client.get(reverse("historial-repartidor", args=[999999]))

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], MSG_REPARTIDOR_NO_ENCONTRADO)

    def test_metodo_distinto_de_get_devuelve_405(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.coordinador)
        resp = cliente.post(self.url_historial(self.juan))

        self.assertEqual(resp.status_code, 405)

    def test_no_hay_consultas_por_entrega(self):
        """``select_related`` resuelve cliente, comercio y comprobante en un JOIN."""
        # 1 sesión + 1 usuario (la autorización) + 1 repartidor + 1 paquetes.
        # La cuarta ya trae TODAS las entregas con sus FKs en el mismo JOIN.
        with self.assertNumQueries(4) as consultas:
            resp = self.client.get(self.url_historial(self.juan))

        self.assertEqual(resp.status_code, 200)
        # Las entregas salen en una sola consulta: se agregan más paquetes y la
        # cantidad de queries no cambia.
        for _ in range(5):
            self._paquete(
                repartidor=self.juan,
                estado=Paquete.Estado.ENTREGADO,
                fecha_destino=date(2026, 10, 15),
            )
        with self.assertNumQueries(len(consultas)):
            resp = self.client.get(self.url_historial(self.juan))
        self.assertEqual(len(resp.json()["entregas"]), 7)


class SoloElCoordinadorPuedeVerElHistorialTests(HistorialTestsBase):
    """Regla de la HU: el historial no está disponible sin sesión de coordinador."""

    def setUp(self):
        # Cliente limpio y sin sesión: es lo que pasa si se llama la API directo.
        self.client = Client()

    def test_sin_sesion_no_se_puede_ver_el_listado(self):
        resp = self.client.get(reverse("historial-repartidores"))

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["message"], MSG_SOLO_COORDINADOR)
        self.assertNotIn("repartidores", resp.json())

    def test_sin_sesion_no_se_puede_ver_el_historial_de_un_repartidor(self):
        resp = self.client.get(reverse("historial-repartidor", args=[self.juan.pk]))

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["message"], MSG_SOLO_COORDINADOR)
        self.assertNotIn("entregas", resp.json())

    def test_sin_sesion_ni_siquiera_confirma_si_el_repartidor_existe(self):
        """El 401 va antes de buscar el repartidor: no filtra ids válidos."""
        resp = self.client.get(reverse("historial-repartidor", args=[999999]))

        self.assertEqual(resp.status_code, 401)

    def test_con_la_sesion_del_coordinador_abierta_se_ve_el_historial(self):
        """Flujo real: login por la API (HU #4) y después consulta del historial."""
        login = self.client.post(
            reverse("login-coordinador"),
            {"username": "coordinador", "password": self.clave},
            content_type="application/json",
        )
        self.assertEqual(login.status_code, 200)

        listado = self.client.get(reverse("historial-repartidores"))
        historial = self.client.get(
            reverse("historial-repartidor", args=[self.juan.pk])
        )

        self.assertEqual(listado.status_code, 200)
        self.assertEqual(historial.status_code, 200)
        self.assertEqual(historial.json()["total_entregas"], 2)
