from django.urls import path

from . import views

# Se monta bajo /api/ en el urls.py principal → GET/POST /api/cambiar-estado-pedido/
urlpatterns = [
    path("cambiar-estado-pedido/", views.cambiar_estado_pedido, name="cambiar-estado-pedido"),
]