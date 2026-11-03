"""Tests de la HU #25: alta de repartidor."""

import json

from django.test import TestCase
from django.urls import reverse

from core.models import Repartidor
from crudRepartidor.views import (
    MSG_ALTA_EXITOSA,
    MSG_CAMPO_OBLIGATORIO,
    MSG_DATO_REPETIDO,
)


class AltaRepartidorTests(TestCase):
    def setUp(self):
        self.url = reverse("crud-repartidor")
        # Datos de un alta válida
        self.datos = {
            "dni": 22222222,
            "nombre": "Luis",
            "apellido": "Gil",
            "telefono": "456",
            "mail": "luis@mail.com",
            "tipo_vehiculo": "moto",
        }

    def _post(self, payload):
        return self.client.post(
            self.url, data=json.dumps(payload), content_type="application/json"
        )

    def test_escenario_1_alta_exitosa(self):
        r = self._post(self.datos)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["message"], MSG_ALTA_EXITOSA)
        # Se guardó en la base y el sistema le generó el token
        repartidor = Repartidor.objects.get(dni=22222222)
        self.assertTrue(repartidor.token)
        self.assertEqual(r.json()["repartidor"]["token"], repartidor.token)

    def test_escenario_2_campo_en_blanco(self):
        datos = {**self.datos, "nombre": ""}
        r = self._post(datos)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["nombre"], MSG_CAMPO_OBLIGATORIO)
        # No se creó ningún repartidor
        self.assertEqual(Repartidor.objects.count(), 0)

    def test_escenario_3_dato_repetido(self):
        # Ya existe un repartidor con ese DNI
        Repartidor.objects.create(
            nombre="Ana", apellido="Paz", dni=22222222,
            telefono="123", mail="ana@mail.com",
        )
        r = self._post(self.datos)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["dni"], MSG_DATO_REPETIDO)
        # Sigue habiendo un solo repartidor
        self.assertEqual(Repartidor.objects.count(), 1)


    def test_nombre_y_apellido_se_guardan_con_mayuscula_inicial(self):
        payload = {
            "dni": "30777666", "nombre": "  jUAN   carlos ", "apellido": "PÉREZ",
            "telefono": "1155551234", "mail": "Juan.Perez@MAIL.com",
            "tipo_vehiculo": "moto",
        }
        r = self.client.post(
            reverse("crud-repartidor"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        repartidor = Repartidor.objects.get(dni=30777666)
        self.assertEqual(repartidor.nombre, "Juan Carlos")
        self.assertEqual(repartidor.apellido, "Pérez")
        self.assertEqual(repartidor.mail, "juan.perez@mail.com")