"""
Rutas principales del backend.

- /admin/     panel de administración de Django.
- /api/...    endpoints que consume el frontend React.
- /media/...  archivos subidos (comprobantes), solo en desarrollo.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core import views

# Títulos que se ven en las pantallas del panel de administración.
admin.site.site_header = "SRFR — Administración"
admin.site.site_title = "SRFR Admin"
admin.site.index_title = "Panel de gestión"

urlpatterns = [
    path("admin/", admin.site.urls),
    # Endpoint de prueba: confirma que la API está viva y que el frontend
    # puede comunicarse (lo usamos para verificar el CORS).
    path("api/ping/", views.ping, name="ping"),
    path("api/", include("crudComercios.urls")),
    path("api/", include("crudRepartidor.urls")),
    path("api/", include("loginCoordinador.urls")),
    path("api/", include("loginRepartidor.urls")),
    path("api/", include("ingresarPedido.urls")),
    # GET/POST /api/cambiar-estado-pedido/
    path("api/", include("actualizacionEstado.urls")),
    path("api/", include("repartidoresDisponibles.urls")),
    path("api/", include("paquetesEnCurso.urls")),
    path("api/", include("historialEnvios.urls")),
]

# En desarrollo Django sirve los archivos subidos (comprobantes) desde
# media/. En producción eso lo resuelve el servidor web o un storage.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
