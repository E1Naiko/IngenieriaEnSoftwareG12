from django.urls import path

from . import views

# Se monta bajo /api/ en config/urls.py.
urlpatterns = [
    path("logout-coordinador/", views.logout_coordinador, name="logout-coordinador"),
    path("login-coordinador/", views.login_coordinador, name="login-coordinador"),
]
