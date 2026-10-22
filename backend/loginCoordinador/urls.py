from django.urls import path

from . import views

# Se monta bajo /api/ en config/urls.py → POST /api/login-coordinador2/
urlpatterns = [
    path("login-coordinador/", views.login_coordinador, name="login-coordinador"),
]
