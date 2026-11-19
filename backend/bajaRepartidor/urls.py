from django.urls import path
from . import views

# Se monta bajo /api/ en config/urls.py
urlpatterns = [
    path("repartidores/<int:repartidor_id>/", views.repartidor_detalle, name="baja-repartidor-detalle"),
    path("repartidores/<int:repartidor_id>/baja/", views.repartidor_baja, name="baja-repartidor"),
]