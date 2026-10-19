"""
Rutas de la API de comercios.

Incluido en ``config/urls.py`` bajo ``path("api/", include("crudComercios.urls"))``,
por lo que todas las rutas heredan el prefijo ``/api/``.

Tabla de rutas
--------------
- GET    /api/comercios/        → ``comercios_list``  (lista con ?q=)
- POST   /api/comercios/        → ``comercios_list``  (crea)
- GET    /api/comercios/<pk>/   → ``comercio_detail`` (detalle)
- PUT    /api/comercios/<pk>/   → ``comercio_detail`` (reemplazo total)
- PATCH  /api/comercios/<pk>/   → ``comercio_detail`` (parcial)
- DELETE /api/comercios/<pk>/   → ``comercio_detail`` (borra)

Nombre de rutas para ``reverse()``: ``comercios-list`` y ``comercio-detail``.
"""

from django.urls import path

from . import views

urlpatterns = [
    path("comercios/", views.comercios_list, name="comercios-list"),
    path("comercios/<int:pk>/", views.comercio_detail, name="comercio-detail"),
]
