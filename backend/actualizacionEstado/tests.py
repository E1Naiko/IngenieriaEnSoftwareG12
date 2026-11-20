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

    def test_post_cambiar_estado_a_entregado_con_dni_correcto(self):
        """HU #23: entregar exige el DNI del cliente; acá el DNI es 30111222."""
        Paquete.objects.filter(pk=self.paquete.pk).update(estado=Paquete.Estado.EN_CAMINO)
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
        for estado, extra in (
            ("en_camino", {}),
            # HU #23: la entrega pide el DNI del cliente (30111222 en setUp).
            ("entregado", {"dni_receptor": 30111222}),
        ):
            r = self._post(
                {
                    "token": self.repartidor.token,
                    "id": self.paquete.id,
                    "estado": estado,
                    **extra,
                }
            )
            self.assertEqual(r.status_code, 200, r.content)
            self.paquete.refresh_from_db()
            self.assertEqual(self.paquete.estado, estado)

    def test_el_get_sigue_siendo_publico(self):
        """La pantalla de seguimiento (HU #14) no manda token y debe seguir andando."""
        r = self.client.get(self.url, {"cod_seguimiento": self.paquete.cod_seguimiento})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["paquetes"]), 1)

class ValidarEntregaConDNITests(TestCase):
    """HU #23 — Validar la entrega con el número del DNI del receptor.

    La regla de la historia es *comprobar* el DNI del cliente, no solo
    adjuntarlo: si no coincide, el paquete no pasa a entregado. Todo el flujo
    pasa por las validaciones de token y propiedad del paquete (HU #38), así
    que cada request manda el token del repartidor asignado.
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

    def _post(self, payload):
        return self.client.post(
            self.url,
            data=json.dumps({"token": self.repartidor.token, **payload}),
            content_type="application/json",
        )

    def _entregar(self, **extra):
        return self.client.post(
            self.url,
            data=json.dumps(
                {
                    "token": self.repartidor.token,
                    "id": self.paquete.id,
                    "estado": "entregado",
                    **extra,
                }
            ),
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
            data=json.dumps(
                {
                    "token": self.repartidor.token,
                    "id": self.paquete.id,
                    "estado": "en_camino",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self._estado(), "en_camino")

    # --- Interacción con las validaciones de la HU #38 --------------------
    def test_sin_token_no_llega_a_la_validacion_de_dni(self):
        """Primero se autentica; el DNI se pide recién después."""
        r = self.client.post(
            self.url,
            data=json.dumps({"id": self.paquete.id, "estado": "entregado"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["message"], "Falta el token")
        self.assertEqual(self._estado(), "en_camino")

    def test_otro_repartidor_no_puede_entregar_un_paquete_ajeno_con_el_dni(self):
        otro = Repartidor.objects.create(
            nombre="Luis", apellido="Sosa", dni=20999888,
            telefono="221-555-0400", mail="luis@example.com",
        )
        r = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "token": otro.token,
                    "id": self.paquete.id,
                    "estado": "entregado",
                    "dni_receptor": 30111222,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)
        self.assertIn("no está asignado", r.json()["message"])
        self.assertEqual(self._estado(), "en_camino")

    # --- Comprobante (foto) opcional -------------------------------------
    def test_la_foto_es_opcional(self):
        r = self._entregar(dni_receptor=30111222)
        self.assertEqual(r.status_code, 200)
        self.paquete.refresh_from_db()
        self.assertIsNone(self.paquete.comprobante)

    def test_guarda_el_comprobante_cuando_llega_la_foto(self):
        import base64 as b64

        from django.core.files.uploadedfile import SimpleUploadedFile

        from core.models import Comprobante

        imagen = SimpleUploadedFile(
            "dni.jpg", b"\xff\xd8\xff\xe0contenido", content_type="image/jpeg"
        )
        data_url = "data:image/jpeg;base64," + b64.b64encode(imagen.read()).decode()
        r = self._entregar(dni_receptor=30111222, foto_dni=data_url)
        self.assertEqual(r.status_code, 200)
        self.paquete.refresh_from_db()
        self.assertIsNotNone(self.paquete.comprobante)
        self.assertEqual(Comprobante.objects.count(), 1)
        self.assertTrue(self.paquete.comprobante.file.name.startswith("comprobantes/"))

    def test_foto_mal_formada_avisa_sin_descartarla_en_silencio(self):
        r = self._entregar(
            dni_receptor=30111222, foto_dni="data:image/jpeg;base64,@@@no-es-base64@@@"
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self._estado(), "en_camino")

    def test_formato_de_foto_no_admitido(self):
        r = self._entregar(
            dni_receptor=30111222, foto_dni="data:application/pdf;base64,QUJD"
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self._estado(), "en_camino")

    # --- Cancelación desde el panel del repartidor ---
    def test_cancelacion_directa_del_desplegable_acepta_motivo_opcional(self):
        for estado, motivo in (("pendiente_reasignacion", ""), ("en_devolucion", None), ("cancelado", "  Otro motivo  ")):
            with self.subTest(estado=estado):
                Paquete.objects.filter(pk=self.paquete.pk).update(
                    estado=Paquete.Estado.EN_CAMINO,
                    repartidor=self.repartidor,
                )
                cuerpo = {"id": self.paquete.id, "estado": estado}
                if motivo is not None:
                    cuerpo["motivo"] = motivo
                r = self._post(cuerpo)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.json()["paquete"]["estado"], estado)
                self.paquete.refresh_from_db()
                self.assertEqual(self.paquete.motivo_cancelacion, (motivo or "").strip())
                if estado == "pendiente_reasignacion":
                    self.assertIsNone(self.paquete.repartidor_id)
                    self.assertEqual(self.paquete.repartidor_original_id, self.repartidor.pk)
                else:
                    self.assertEqual(self.paquete.repartidor_id, self.repartidor.pk)
                    self.assertIsNone(self.paquete.reasignacion_hasta)

    def test_cancelacion_compatible_rechaza_una_causa_explicita_invalida(self):
        r = self._post({"id": self.paquete.id, "estado": "cancelado", "motivo": "Se rompió", "causa": None})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["campo"], "causa")

    def test_el_desplegable_permite_confirmar_una_devolucion_sin_causa(self):
        paquete = {"id": self.paquete.pk}
        self.assertEqual(self._post({**paquete, "estado": "en_devolucion"}).status_code, 200)
        self.assertEqual(self._post({**paquete, "estado": "pendiente_reasignacion"}).status_code, 409)
        r = self._post({**paquete, "estado": "cancelado"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["paquete"]["estado"], "cancelado")

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

    # --- Separación de los dos cierres por cancelación ---
    def test_rechazo_del_cliente_cierra_como_cancelado_por_cliente(self):
        r = self._post({
            "id": self.paquete.id, "estado": "cancelado",
            "causa": "cliente_rechaza", "motivo": "No lo quiso recibir",
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["paquete"]["estado"], Paquete.Estado.CANCELADO_POR_CLIENTE)
        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.estado, Paquete.Estado.CANCELADO_POR_CLIENTE)
        # Sigue en manos del repartidor: no hay reasignación ni oferta.
        self.assertEqual(self.paquete.repartidor_id, self.repartidor.pk)
        self.assertIsNone(self.paquete.reasignacion_hasta)
        self.assertIsNone(self.paquete.repartidor_original_id)

    def test_cancelado_por_cliente_no_admite_mas_cambios(self):
        Paquete.objects.filter(pk=self.paquete.pk).update(
            estado=Paquete.Estado.CANCELADO_POR_CLIENTE
        )
        for nuevo in ("en_camino", "entregado", "cancelado"):
            with self.subTest(nuevo=nuevo):
                r = self._post({"id": self.paquete.id, "estado": nuevo})
                self.assertEqual(r.status_code, 400)
                self.assertIn("No se puede modificar", r.json()["message"])
        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.estado, Paquete.Estado.CANCELADO_POR_CLIENTE)

    def test_los_dos_cierres_son_estados_distintos(self):
        """El cierre genérico se distingue del rechazo explícito."""
        self.assertNotEqual(
            Paquete.Estado.CANCELADO, Paquete.Estado.CANCELADO_POR_CLIENTE
        )
        self.assertIn(Paquete.Estado.CANCELADO.lower(), Paquete.ESTADOS_CERRADOS)
        self.assertIn(Paquete.Estado.CANCELADO_POR_CLIENTE.lower(), Paquete.ESTADOS_CERRADOS)
        self.assertNotIn(Paquete.Estado.EN_DEVOLUCION.lower(), Paquete.ESTADOS_CERRADOS)
        self.assertNotIn(Paquete.Estado.PENDIENTE_REASIGNACION.lower(), Paquete.ESTADOS_CERRADOS)

    def test_confirmar_devolucion_limpia_el_punto_de_retiro(self):
        Paquete.objects.filter(pk=self.paquete.pk).update(
            estado=Paquete.Estado.EN_DEVOLUCION,
            retiro_latitud=-34.92, retiro_longitud=-57.95,
        )
        r = self._post({"id": self.paquete.id, "estado": "cancelado"})
        self.assertEqual(r.status_code, 200)
        self.paquete.refresh_from_db()
        self.assertEqual(self.paquete.estado, Paquete.Estado.CANCELADO)
        self.assertIsNone(self.paquete.retiro_latitud)
        self.assertIsNone(self.paquete.retiro_longitud)
