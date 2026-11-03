from django.urls import path

from . import views

# Se monta bajo /api/ en config/urls.py
#   GET /api/historial/        -> lista de repartidores
#   GET /api/historial/<id>/   -> historial de un repartidor
urlpatterns = [
    path("historial/", views.historial_lista, name="historial-lista"),
    path("historial/<int:pk>/", views.historial_repartidor, name="historial-repartidor"),
]