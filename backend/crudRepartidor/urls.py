from django.urls import path

from . import views

# Se monta bajo /api/ en config/urls.py → POST /api/repartidores/
urlpatterns = [
    path("repartidores/", views.repartidores_alta, name="crud-repartidor"),
]