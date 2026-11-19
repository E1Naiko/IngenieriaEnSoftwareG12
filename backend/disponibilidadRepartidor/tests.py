"""Tests del cambio de disponibilidad del repartidor."""

import json

from django.test import TestCase
from django.urls import reverse

from core.models import Repartidor
from disponibilidadRepartidor.views import (
    MSG_DISPONIBLE,
    MSG_ESTADO_INVALIDO,
    MSG_FALTA_TOKEN,
    MSG_NO_DISPONIBLE,
    MSG_REPARTIDOR_BAJA,
    MSG_TOKEN_INVALIDO,
)


class CambiarDisponibilidadTests(TestCase):
    def setUp(self):
        self.url = reverse("disponibilidad-repartidor")

    def _crear(self, estado="ACTIVO"):
        # El token lo genera el modelo al guardar.
        return Repartidor.objects.create(
            nombre="Ana", apellido="Paz", dni=11111111,
            telefono="123", mail="ana@mail.com",
            tipo_vehiculo="moto", estado=estado,
        )

    def _post(self, payload):
        return self.client.post(
            self.url, data=json.dumps(payload), content_type="application/json"
        )
    def test_pasa_a_no_disponible(self):
        r = self._crear("ACTIVO")
        resp = self._post({"token": r.token, "estado": "no_disponible"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["message"], MSG_NO_DISPONIBLE)
        self.assertEqual(resp.json()["estado"], "inactivo")
        r.refresh_from_db()
        self.assertEqual(r.estado, "inactivo")

    def test_pasa_a_disponible(self):
        r = self._crear("inactivo")
        resp = self._post({"token": r.token, "estado": "disponible"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["message"], MSG_DISPONIBLE)
        self.assertEqual(resp.json()["estado"], "activo")
        self.assertTrue(resp.json()["disponible"])
        r.refresh_from_db()
        self.assertEqual(r.estado, "ACTIVO")

    def test_acepta_mayusculas_y_espacios(self):
        r = self._crear("ACTIVO")
        resp = self._post({"token": f" {r.token.lower()} ", "estado": " INACTIVO "})
        self.assertEqual(resp.status_code, 200)
        r.refresh_from_db()
        self.assertEqual(r.estado, "inactivo")

    def test_acepta_tambien_los_valores_del_modelo(self):
        r = self._crear("ACTIVO")
        self.assertEqual(self._post({"token": r.token, "estado": "inactivo"}).status_code, 200)
        r.refresh_from_db()
        self.assertEqual(r.estado, "inactivo")
        self.assertEqual(self._post({"token": r.token, "estado": "activo"}).status_code, 200)
        r.refresh_from_db()
        self.assertEqual(r.estado, "ACTIVO")

    def test_mismo_estado_no_da_error(self):
        r = self._crear("ACTIVO")
        resp = self._post({"token": r.token, "estado": "activo"})
        self.assertEqual(resp.status_code, 200)
        r.refresh_from_db()
        self.assertEqual(r.estado, "ACTIVO")

    def test_estado_invalido(self):
        r = self._crear("ACTIVO")
        resp = self._post({"token": r.token, "estado": "baja"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json(), {"estado": MSG_ESTADO_INVALIDO})
        r.refresh_from_db()
        self.assertEqual(r.estado, "ACTIVO")

    def test_falta_el_token(self):
        resp = self._post({"estado": "activo"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["message"], MSG_FALTA_TOKEN)

    def test_token_inexistente(self):
        resp = self._post({"token": "ZZZZZZ", "estado": "activo"})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["message"], MSG_TOKEN_INVALIDO)

    def test_repartidor_dado_de_baja_no_puede_cambiar(self):
        r = self._crear("baja")
        resp = self._post({"token": r.token, "estado": "activo"})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["message"], MSG_REPARTIDOR_BAJA)
        r.refresh_from_db()
        self.assertEqual(r.estado, "baja")

    def test_json_invalido(self):
        resp = self.client.post(
            self.url, data="esto no es json", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_metodo_no_permitido(self):
        resp = self.client.put(self.url)
        self.assertEqual(resp.status_code, 405)

    def test_get_devuelve_estado_disponible(self):
        r = self._crear("ACTIVO")
        resp = self.client.get(self.url, {"token": r.token})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"estado": "activo", "disponible": True})

    def test_get_devuelve_estado_no_disponible(self):
        r = self._crear("inactivo")
        resp = self.client.get(self.url, {"token": r.token})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"estado": "inactivo", "disponible": False})

    def test_get_trata_disponible_en_mayusculas_como_disponible(self):
        # En la base de desarrollo hay repartidores con "DISPONIBLE".
        r = self._crear("DISPONIBLE")
        resp = self.client.get(self.url, {"token": r.token})
        self.assertEqual(resp.json(), {"estado": "activo", "disponible": True})

    def test_get_sin_token(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["message"], MSG_FALTA_TOKEN)

    def test_get_token_inexistente(self):
        resp = self.client.get(self.url, {"token": "ZZZZZZ"})
        self.assertEqual(resp.status_code, 404)

    def test_get_repartidor_dado_de_baja(self):
        r = self._crear("baja")
        resp = self.client.get(self.url, {"token": r.token})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["message"], MSG_REPARTIDOR_BAJA)