from django.urls import path

from . import views

# Se monta bajo /api/ en config/urls.py → /api/pedidos/ y /api/clientes/
urlpatterns = [
    path("pedidos/", views.pedidos_list, name="pedidos-list"),
    path("clientes/", views.clientes_list, name="clientes-list"),
]
