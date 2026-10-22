"""Tests de la HU #4: un caso por escenario, más los bordes de la API."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .views import MSG_CREDENCIALES, MSG_FALTAN_CAMPOS


class LoginCoordinadorTests(TestCase):
    def setUp(self):
        self.url = reverse("login-coordinador")
        self.user = User.objects.create_user(username="coordinador", password="clave-segura-123")

    def post(self, data):
        return self.client.post(self.url, data, content_type="application/json")

    def test_login_exitoso(self):  # escenario 1
        r = self.post({"username": "coordinador", "password": "clave-segura-123"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("_auth_user_id", self.client.session)  # quedó la sesión iniciada

    def test_faltan_campos(self):  # escenario 2
        for data in ({"password": "x"}, {"username": "coordinador"}, {"username": " ", "password": ""}):
            with self.subTest(data=data):
                r = self.post(data)
                self.assertEqual(r.status_code, 400)
                self.assertEqual(r.json()["message"], MSG_FALTAN_CAMPOS)

    def test_credenciales_invalidas(self):  # escenario 3
        for data in ({"username": "coordinador", "password": "mal"}, {"username": "nadie", "password": "x"}):
            with self.subTest(data=data):
                r = self.post(data)
                self.assertEqual(r.status_code, 401)
                self.assertEqual(r.json()["message"], MSG_CREDENCIALES)

    def test_usuario_desactivado(self):
        self.user.is_active = False
        self.user.save()
        r = self.post({"username": "coordinador", "password": "clave-segura-123"})
        self.assertEqual(r.status_code, 401)

    def test_json_invalido(self):
        r = self.client.post(self.url, "no es json", content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_solo_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
