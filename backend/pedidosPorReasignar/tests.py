"""Tests de la HU #36: ver y tomar pedidos "Por Reasignar".

La lista se arma con los paquetes ``cancelado`` (lo que deja el botón
"Confirmar cancelación" del dashboard) y muestra el nombre y apellido del
último repartidor leyendo directamente ``paquete.repartidor``. No hay estado
nuevo ni campos nuevos en el modelo.
"""

import datetime
import json

from django.test import TestCase
from django.urls import reverse

from core.models import Cliente, Comercio, Paquete, Repartidor


class PedidosPorReasignarTests(TestCase):
    def setUp(self):
        self.url_lista = reverse("pedidos-por-reasignar")
        self.url_aceptar = lambda pk: reverse(
            "pedidos-por-reasignar-aceptar", args=[pk]
        )
        self.url_asignados = reverse("paquetes-repartidor")
        self.url_cambiar_estado = reverse("cambiar-estado-pedido")

        self.repartidor = Repartidor.objects.create(
            nombre="Ana", apellido="Paz", dni=11111111,
            telefono="123", mail="ana@mail.com",
        )
        self.otro = Repartidor.objects.create(
            nombre="Luis", apellido="Sosa", dni=22222222,
            telefono="456", mail="luis@mail.com",
        )
        self.anterior = Repartidor.objects.create(
            nombre="Marta", apellido="López", dni=33333333,
            telefono="789", mail="marta@mail.com",
        )
        self.comercio = Comercio.objects.create(
            nombre="Kiosco", telefono="1", direccion="Calle 1 #23"
        )
        self.cliente = Cliente.objects.create(
            nombre="Juan", apellido="Pérez", telefono="2",
            direccion="Calle 2 #45", dni=44444444,
        )

    def _paquete(self, estado=Paquete.Estado.CANCELADO, **kwargs):
        return Paquete.objects.create(
            comercio=self.comercio,
            cliente=self.cliente,
            estado=estado,
            fecha_origen=datetime.date(2026, 10, 29),
            fecha_destino=datetime.date(2026, 10, 30),
            **kwargs,
        )

    def _post(self, url, payload=None, body=None):
        return self.client.post(
            url,
            data=body if body is not None else json.dumps(payload or {}),
            content_type="application/json",
        )

    def _lista(self, token=None):
        return self._post(self.url_lista, {"token": token or self.repartidor.token})

    def _aceptar(self, pk, token=None):
        return self._post(
            self.url_aceptar(pk), {"token": token or self.repartidor.token}
        )

    # --- Escenario 2: lista vacía ------------------------------------------

    def test_escenario_2_lista_vacia(self):
        r = self._lista()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["pedidos"], [])
        self.assertIn("mensaje", r.json())

    def test_solo_los_cancelados_entran_en_la_lista(self):
        """Sin filtro de zona: todo ``cancelado`` se publica, nada más."""
        cancelado = self._paquete(repartidor=self.anterior)
        cancelado_mayusculas = self._paquete("CANCELADO", repartidor=self.anterior)
        for estado in (
            Paquete.Estado.PENDIENTE,
            Paquete.Estado.ASIGNADO,
            Paquete.Estado.RETIRADO,
            Paquete.Estado.EN_CAMINO,
            Paquete.Estado.ENTREGADO,
        ):
            self._paquete(estado, repartidor=self.anterior)

        r = self._lista()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            {p["id"] for p in r.json()["pedidos"]},
            {cancelado.id, cancelado_mayusculas.id},
        )

    # --- Contrato: solo lo necesario + último repartidor --------------------

    def test_cada_pedido_muestra_solo_lo_necesario(self):
        self._paquete(tamanio="mediano", repartidor=self.anterior)
        pedido = self._lista().json()["pedidos"][0]
        self.assertEqual(
            set(pedido),
            {
                "id",
                "direccion_retiro",
                "direccion_destino",
                "tamanio",
                "ultimo_repartidor",
            },
        )
        self.assertEqual(pedido["direccion_retiro"], "Calle 1 #23")
        self.assertEqual(pedido["direccion_destino"], "Calle 2 #45")
        self.assertEqual(pedido["tamanio"], "mediano")

    def test_muestra_directamente_la_ultima_persona_que_lo_tuvo(self):
        """Nombre y apellido salen de la FK ``repartidor``, sin campos nuevos."""
        self._paquete(repartidor=self.anterior)
        pedido = self._lista().json()["pedidos"][0]
        self.assertEqual(
            pedido["ultimo_repartidor"],
            {"nombre": "Marta", "apellido": "López"},
        )

    def test_cancelado_sin_repartidor_devuelve_ultimo_repartidor_nulo(self):
        self._paquete(repartidor=None)
        self.assertIsNone(self._lista().json()["pedidos"][0]["ultimo_repartidor"])

    # --- Regla: token único + operativo -------------------------------------

    def test_token_inexistente(self):
        r = self._lista("ZZZZZZ")
        self.assertEqual(r.status_code, 404)
        self.assertIn("message", r.json())

    def test_falta_el_token(self):
        self.assertEqual(self._post(self.url_lista, {}).status_code, 400)

    def test_body_no_es_json(self):
        self.assertEqual(
            self._post(self.url_lista, body="{no-json").status_code, 400
        )

    def test_repartidor_no_operativo_no_ve_la_lista(self):
        for estado in (Repartidor.Estado.INACTIVO, Repartidor.Estado.BAJA):
            with self.subTest(estado=estado):
                self.repartidor.estado = estado
                self.repartidor.save(update_fields=["estado"])
                r = self._lista()
                self.assertEqual(r.status_code, 403)
                self.assertIn("message", r.json())

    def test_get_no_permitido(self):
        self.assertEqual(self.client.get(self.url_lista).status_code, 405)

    # --- Escenario 1: toma exitosa -----------------------------------------

    def test_escenario_1_toma_exitosa_y_aparece_en_sus_asignados(self):
        pedido = self._paquete(repartidor=self.anterior)
        r = self._aceptar(pedido.id)
        self.assertEqual(r.status_code, 200)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Paquete.Estado.ASIGNADO)
        self.assertEqual(pedido.repartidor_id, self.repartidor.id)

        # Ya figura en la lista de pedidos asignados (HU #17)...
        asignados = self._post(
            self.url_asignados, {"token": self.repartidor.token}
        ).json()["paquetes"]
        self.assertIn(pedido.id, [p["id"] for p in asignados])

        # ...y desapareció de la lista de reasignación para todos.
        self.assertEqual(self._lista().json()["pedidos"], [])
        self.assertEqual(self._lista(self.otro.token).json()["pedidos"], [])

    def test_respuesta_del_aceptar(self):
        pedido = self._paquete(repartidor=self.anterior)
        datos = self._aceptar(pedido.id).json()
        self.assertEqual(datos["message"], "Pedido aceptado")
        self.assertEqual(
            datos["pedido"], {"id": pedido.id, "estado": Paquete.Estado.ASIGNADO}
        )

    def test_puede_tomar_aunque_ya_tenga_otros_pedidos_asignados(self):
        self._paquete(Paquete.Estado.ASIGNADO, repartidor=self.repartidor)
        self._paquete(Paquete.Estado.EN_CAMINO, repartidor=self.repartidor)
        pedido = self._paquete(repartidor=self.anterior)
        self.assertEqual(self._aceptar(pedido.id).status_code, 200)
        pedido.refresh_from_db()
        self.assertEqual(pedido.repartidor_id, self.repartidor.id)

    # --- Regla: el primero que lo toma se lo queda --------------------------

    def test_el_primero_que_lo_toma_se_lo_queda(self):
        pedido = self._paquete(repartidor=self.anterior)
        self.assertEqual(self._aceptar(pedido.id).status_code, 200)

        r = self._aceptar(pedido.id, self.otro.token)
        self.assertEqual(r.status_code, 409)
        self.assertIn("message", r.json())
        pedido.refresh_from_db()
        self.assertEqual(pedido.repartidor_id, self.repartidor.id)
        self.assertEqual(pedido.estado, Paquete.Estado.ASIGNADO)
        ajenos = self._post(
            self.url_asignados, {"token": self.otro.token}
        ).json()["paquetes"]
        self.assertNotIn(pedido.id, [p["id"] for p in ajenos])

    def test_no_se_puede_tomar_un_pedido_que_no_esta_cancelado(self):
        for estado in (Paquete.Estado.PENDIENTE, Paquete.Estado.ASIGNADO,
                       Paquete.Estado.ENTREGADO):
            with self.subTest(estado=estado):
                pedido = self._paquete(estado, repartidor=self.anterior)
                self.assertEqual(self._aceptar(pedido.id).status_code, 409)
                pedido.refresh_from_db()
                self.assertEqual(pedido.estado, estado)
                self.assertEqual(pedido.repartidor_id, self.anterior.id)

    def test_aceptar_pedido_inexistente(self):
        self.assertEqual(self._aceptar(99999).status_code, 404)

    def test_aceptar_tambien_exige_token_y_estado_operativo(self):
        pedido = self._paquete(repartidor=self.anterior)
        self.assertEqual(self._aceptar(pedido.id, "ZZZZZZ").status_code, 404)
        self.repartidor.estado = Repartidor.Estado.BAJA
        self.repartidor.save(update_fields=["estado"])
        self.assertEqual(self._aceptar(pedido.id).status_code, 403)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Paquete.Estado.CANCELADO)
        self.assertEqual(pedido.repartidor_id, self.anterior.id)

    # --- Flujo real: la cancelación del front alimenta la lista ------------

    def test_flujo_completo_cancelar_listar_y_tomar(self):
        """Reproduce lo que hacen los dos componentes de React."""
        pedido = self._paquete(
            Paquete.Estado.ASIGNADO, repartidor=self.anterior
        )

        # 1) Dashboardrepartidor.tsx: "Confirmar cancelación" con motivo.
        cancelacion = self._post(
            self.url_cambiar_estado,
            {
                "token": self.anterior.token,
                "id": pedido.id,
                "estado": Paquete.Estado.CANCELADO,
                "motivo": "No pude completar la entrega",
            },
        )
        self.assertEqual(cancelacion.status_code, 200)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Paquete.Estado.CANCELADO)
        # La cancelación NO limpia la FK: de ahí sale el nombre y apellido.
        self.assertEqual(pedido.repartidor_id, self.anterior.id)
        self.assertEqual(
            self._post(
                self.url_asignados, {"token": self.anterior.token}
            ).json()["paquetes"],
            [],
        )

        # 2) PedidosPorReasignar.tsx: la lista lo muestra con quién lo tuvo.
        datos = self._lista(self.otro.token).json()["pedidos"]
        self.assertEqual([p["id"] for p in datos], [pedido.id])
        self.assertEqual(
            datos[0]["ultimo_repartidor"],
            {"nombre": "Marta", "apellido": "López"},
        )

        # 3) Otro repartidor lo acepta y pasa a sus asignados.
        self.assertEqual(self._aceptar(pedido.id, self.otro.token).status_code, 200)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Paquete.Estado.ASIGNADO)
        self.assertEqual(pedido.repartidor_id, self.otro.id)
        asignados = self._post(
            self.url_asignados, {"token": self.otro.token}
        ).json()["paquetes"]
        self.assertIn(pedido.id, [p["id"] for p in asignados])
        self.assertEqual(self._lista().json()["pedidos"], [])
