"""Tests de la HU #9: login del repartidor"""
import json
from django.test import TestCase
from django.urls import reverse
from core.models import Repartidor

MSG_TOKEN_INVALIDO = "Token inválido"
MSG_REPARTIDOR_BAJA = (
    "El repartidor no se encuentra habilitado. Comuníquese con el coordinador"
)


class LoginRepartidorTests(TestCase):
    def setUp(self):
        self.url = reverse("login-repartidor")
        # El token se genera solo al crear el repartidor
        self.repartidor = Repartidor.objects.create(
            nombre="Ana", apellido="Paz", dni=11111111,
            telefono="123", mail="ana@mail.com",
        )

    def _post(self, payload):
        return self.client.post(
            self.url, data=json.dumps(payload), content_type="application/json"
        )

    def test_escenario_1_login_exitoso(self):
        r = self._post({"token": self.repartidor.token})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["id"], self.repartidor.id)

    def test_escenario_2_token_invalido(self):
        r = self._post({"token": "ZZZZ"})
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["message"], MSG_TOKEN_INVALIDO )



    def test_escenario_3_repartidor_dado_de_baja(self):
        self.repartidor.estado = "baja"
        self.repartidor.save()
        r = self._post({"token": self.repartidor.token})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["message"], MSG_REPARTIDOR_BAJA)