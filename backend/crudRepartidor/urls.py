from django.urls import path

from . import views

# Se monta bajo /api/ en config/urls.py → POST /api/crud-repartidor/
urlpatterns = [
    path("crud-repartidor/", views.repartidores_alta, name="crud-repartidor"),
]