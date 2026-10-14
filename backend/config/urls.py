from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from login import views

admin.site.site_header = "Login — Administración"
admin.site.site_title = "Login Admin"
admin.site.index_title = "Panel de gestión"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/ping/", views.ping, name="ping"),
]

# En desarrollo servimos los archivos subidos (comprobantes) desde Django.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
