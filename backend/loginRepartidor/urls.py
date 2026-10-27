from django.urls import path

from . import views

# Se monta bajo /api/ en config/urls.py → POST /api/login-repartidor/
urlpatterns = [
    path("login-repartidor/", views.login_repartidor, name="login-repartidor"),
]
