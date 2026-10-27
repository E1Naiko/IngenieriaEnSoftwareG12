
from django.urls import path

from . import views

# Se monta bajo /api/ en config/urls.py → POST /api/dashboard/
urlpatterns = [
    path("dashboard/paquetes/", views.paquetesEnCurso, name="paquetesEnCurso"),
]
