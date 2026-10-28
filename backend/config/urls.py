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

    # Endpoint de prueba para verificar que la API responde.
    path("api/ping/", views.ping, name="ping"),

    # Endpoints de comercios.
    path("api/", include("crudComercios.urls")),

    # Endpoints de login del coordinador.
    path("api/", include("loginCoordinador.urls")),

    # Endpoints de repartidores disponibles.
    path("api/", include("repartidoresDisponibles.urls")),
    path("api/", include("loginRepartidor.urls")),
    path("api/", include("paquetesEnCurso.urls")),
]

# En desarrollo Django sirve los archivos subidos desde media/.
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )