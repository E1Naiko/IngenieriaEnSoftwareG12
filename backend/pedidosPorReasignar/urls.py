from django.urls import path

from . import views

# Se monta bajo /api/ en config/urls.py.
urlpatterns = [
    path("pedidos-por-reasignar/", views.listar, name="pedidos-por-reasignar"),
    path(
        "pedidos-por-reasignar/aceptar/<int:pk>/",
        views.aceptar,
        name="pedidos-por-reasignar-aceptar",
    ),
]
