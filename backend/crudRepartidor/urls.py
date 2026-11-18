from django.urls import path

from . import views

# Se monta bajo /api/ en config/urls.py:
#   POST    /api/repartidores/          → alta de repartidor (HU #25)
#   GET     /api/repartidores/lista/    → lista para elegir a quién editar (HU #39)
#   GET/PUT /api/repartidores/<id>/     → ver y editar un repartidor (HU #39)
urlpatterns = [
    path("repartidores/", views.repartidores_alta, name="crud-repartidor"),
    path("repartidores/lista/", views.repartidores_lista, name="crud-repartidor-lista"),
    path("repartidores/<int:pk>/", views.repartidor_detalle, name="crud-repartidor-detalle"),
]