from django.urls import path

from . import views

# Se monta bajo /api/ en config/urls.py → POST /api/paquetes-repartidor/
urlpatterns = [
    path("pedidos-cercanos/", views.pedidos_cercanos, name="pedidos-cercanos"),
    path("paquetes-repartidor/", views.paquetes_repartidor, name="paquetes-repartidor"),
]
