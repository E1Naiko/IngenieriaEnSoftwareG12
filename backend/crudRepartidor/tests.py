"""Tests de la HU #25 (alta de repartidor) y la HU #39 (edición)."""

import json

from django.test import TestCase
from django.urls import reverse

from core.models import Repartidor
from crudRepartidor.views import (
    MSG_ALTA_EXITOSA,
    MSG_CAMPO_OBLIGATORIO,
    MSG_DATO_REPETIDO,
    MSG_EDICION_EXITOSA,
    MSG_NO_ENCONTRADO,
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


class EditarRepartidorTests(TestCase):
    """Tests de la HU #39: edición de repartidor."""

    def setUp(self):
        # Repartidor que vamos a editar
        self.repartidor = Repartidor.objects.create(
            nombre="Ana", apellido="Paz", dni=11111111,
            telefono="123", mail="ana@mail.com", tipo_vehiculo="moto",
        )
        # Otro repartidor, para probar datos repetidos
        self.otro = Repartidor.objects.create(
            nombre="Luis", apellido="Gil", dni=22222222,
            telefono="456", mail="luis@mail.com", tipo_vehiculo="auto",
        )
        self.url = reverse("crud-repartidor-detalle", args=[self.repartidor.pk])
        # Datos de una edición válida (los mismos de Ana, con otro vehículo)
        self.datos = {
            "dni": 11111111,
            "nombre": "Ana",
            "apellido": "Paz",
            "telefono": "123",
            "mail": "ana@mail.com",
            "tipo_vehiculo": "camioneta",
        }

    def _put(self, payload, url=None):
        return self.client.put(
            url or self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_escenario_1_edicion_exitosa(self):
        token_antes = self.repartidor.token
        r = self._put({**self.datos, "nombre": "  maRIA  ", "mail": "Maria@MAIL.com"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["message"], MSG_EDICION_EXITOSA)
        # Los cambios se guardaron (con el nombre normalizado y el mail en minúscula)
        self.repartidor.refresh_from_db()
        self.assertEqual(self.repartidor.nombre, "Maria")
        self.assertEqual(self.repartidor.mail, "maria@mail.com")
        self.assertEqual(self.repartidor.tipo_vehiculo, "camioneta")
        # El token se mantiene al editar
        self.assertEqual(self.repartidor.token, token_antes)

    def test_escenario_2_campo_en_blanco(self):
        r = self._put({**self.datos, "telefono": "   "})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json(), {"telefono": MSG_CAMPO_OBLIGATORIO})
        # No se modificó nada en la base
        self.repartidor.refresh_from_db()
        self.assertEqual(self.repartidor.telefono, "123")
        self.assertEqual(self.repartidor.tipo_vehiculo, "moto")

    def test_escenario_3_dato_repetido(self):
        # DNI, mail y teléfono de otro repartidor (el mail con otras mayúsculas)
        r = self._put({
            **self.datos,
            "dni": 22222222,
            "mail": "LUIS@mail.com",
            "telefono": "456",
        })
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json(), {
            "dni": MSG_DATO_REPETIDO,
            "mail": MSG_DATO_REPETIDO,
            "telefono": MSG_DATO_REPETIDO,
        })
        # No se modificó nada en la base
        self.repartidor.refresh_from_db()
        self.assertEqual(self.repartidor.dni, 11111111)

    def test_guardar_con_sus_propios_datos_no_es_repetido(self):
        # Mismo DNI, mail y teléfono que ya tiene: no debe chocar consigo mismo
        r = self._put(self.datos)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["message"], MSG_EDICION_EXITOSA)

    def test_dni_no_numerico(self):
        r = self._put({**self.datos, "dni": "abc"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json(), {"dni": "El DNI debe ser un número"})

    def test_tipo_vehiculo_invalido(self):
        r = self._put({**self.datos, "tipo_vehiculo": "bicicleta"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json(), {"tipo_vehiculo": "Tipo de vehículo inválido"})

    def test_json_invalido(self):
        r = self.client.put(
            self.url, data="esto no es json", content_type="application/json"
        )
        self.assertEqual(r.status_code, 400)

    def test_repartidor_inexistente(self):
        url = reverse("crud-repartidor-detalle", args=[999999])
        r = self._put(self.datos, url=url)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["message"], MSG_NO_ENCONTRADO)

    def test_get_devuelve_solo_los_datos_de_la_hu(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        repartidor = r.json()["repartidor"]
        # Sin id ni estado: solo lo que el front necesita
        self.assertEqual(
            set(repartidor),
            {"nombre", "apellido", "dni", "telefono", "mail", "tipo_vehiculo", "token"},
        )
        self.assertEqual(repartidor["token"], self.repartidor.token)

    def test_metodo_no_permitido(self):
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 405)