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

    def test_escenario_3_la_baja_en_mayusculas_tambien_bloquea(self):
        """En la base conviven 'baja' y 'BAJA': la comparación no distingue.

        Antes se comparaba contra el literal "baja": un repartidor con 'BAJA'
        (por ejemplo, una fila migrada) seguía entrando con su token.
        """
        Repartidor.objects.filter(pk=self.repartidor.pk).update(estado="BAJA")

        r = self._post({"token": self.repartidor.token})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["message"], MSG_REPARTIDOR_BAJA)

    def test_escenario_3_con_espacios_alrededor_de_la_baja(self):
        Repartidor.objects.filter(pk=self.repartidor.pk).update(estado=" Baja ")

        r = self._post({"token": self.repartidor.token})
        self.assertEqual(r.status_code, 403)

class RecuperarTokenTests(TestCase):
    """Tests de la HU #29: recuperar el token con el DNI."""

    def setUp(self):
        self.url = reverse("recuperar-token")
        self.repartidor = Repartidor.objects.create(
            nombre="Ana", apellido="Paz", dni=11111111,
            telefono="123", mail="ana@mail.com",
        )

    def _post(self, payload, url=None):
        return self.client.post(
            url or self.url, data=json.dumps(payload), content_type="application/json"
        )

    def test_escenario_1_recuperacion_exitosa(self):
        viejo = self.repartidor.token
        r = self._post({"dni": "11111111"})
        self.assertEqual(r.status_code, 200)
        nuevo = r.json()["token"]
        self.assertNotEqual(nuevo, viejo)
        self.repartidor.refresh_from_db()
        self.assertEqual(self.repartidor.token, nuevo)
        # El token viejo ya no entra y el nuevo sí
        login = reverse("login-repartidor")
        self.assertEqual(self._post({"token": viejo}, login).status_code, 404)
        self.assertEqual(self._post({"token": nuevo}, login).status_code, 200)

    def test_escenario_2_dni_no_registrado(self):
        r = self._post({"dni": 99999999})
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["message"], "Datos incorrectos")

    def test_repartidor_dado_de_baja_no_recupera(self):
        self.repartidor.estado = "baja"
        self.repartidor.save()
        viejo = self.repartidor.token
        r = self._post({"dni": 11111111})
        self.assertEqual(r.status_code, 403)
        self.repartidor.refresh_from_db()
        self.assertEqual(self.repartidor.token, viejo)

    def test_repartidor_dado_de_baja_con_mayusculas_no_recupera(self):
        Repartidor.objects.filter(pk=self.repartidor.pk).update(estado="BAJA")
        viejo = self.repartidor.token

        r = self._post({"dni": 11111111})
        self.assertEqual(r.status_code, 403)

        self.repartidor.refresh_from_db()
        self.assertEqual(self.repartidor.token, viejo)

    def test_datos_invalidos(self):
        self.assertEqual(self._post({}).status_code, 400)
        self.assertEqual(self._post({"dni": "abc"}).status_code, 400)
        r = self.client.post(self.url, data="no json", content_type="application/json")
        self.assertEqual(r.status_code, 400)
