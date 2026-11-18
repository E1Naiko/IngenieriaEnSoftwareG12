from django.urls import path

from . import views

# Se monta bajo /api/ en config/urls.py → POST /api/disponibilidad-repartidor/
urlpatterns = [
    path(
        "disponibilidad-repartidor/",
        views.cambiar_disponibilidad,
        name="disponibilidad-repartidor",
    ),
]