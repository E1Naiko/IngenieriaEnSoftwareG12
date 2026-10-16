"""Rutas de la API de comercios."""
from django.urls import path

from . import views

urlpatterns = [
    path("comercios/", views.comercios_list, name="comercios-list"),
    path("comercios/<int:pk>/", views.comercio_detail, name="comercio-detail"),
]
