from django.urls import path

from . import views

# Se monta bajo /api/ en config/urls.py:
#   GET /api/historial/       → escenario 1 (listado de repartidores)
#   GET /api/historial/<id>/  → escenario 2 (historial de un repartidor)
urlpatterns = [
    path("historial/", views.historial_repartidores, name="historial-repartidores"),
    path("historial/<int:pk>/", views.historial_repartidor, name="historial-repartidor"),
]
