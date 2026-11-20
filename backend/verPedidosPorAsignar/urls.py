from django.urls import path

from . import views

urlpatterns = [
    path("pedidos-cercanos/", views.pedidos_cercanos, name="pedidos-cercanos"),
    path("dashboard/pedidos-por-reasignar/", views.pedidos_por_reasignar, name="dashboard-pedidos-por-reasignar"),
]
