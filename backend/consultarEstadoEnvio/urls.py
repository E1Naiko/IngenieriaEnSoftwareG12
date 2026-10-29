"""Rutas para consultar el estado de un envío."""

from django.urls import path

from . import views

urlpatterns = [
    path(
        "consultar-estado-envio/",
        views.consultar_estado_envio,
        name="consultar-estado-envio",
    ),
]
