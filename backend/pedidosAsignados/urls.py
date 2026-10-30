from django.urls import path

from . import views

# Se monta bajo /api/ en config/urls.py → POST /api/paquetes-repartidor/
urlpatterns = [
    path("paquetes-repartidor/", views.paquetes_repartidor, name="paquetes-repartidor"),
]
