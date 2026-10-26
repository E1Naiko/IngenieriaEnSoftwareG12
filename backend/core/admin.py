"""
Configuración del panel de administración (/admin) para los 5 modelos.

Cada ModelAdmin define qué columnas ver en el listado (list_display),
filtros laterales (list_filter) y el buscador (search_fields), para que
el día a día del equipo no dependa de consultas a mano.
"""

from django.contrib import admin

from .models import Cliente, Comercio, Comprobante, Paquete, Repartidor


@admin.register(Repartidor)
class RepartidorAdmin(admin.ModelAdmin):
    """Alta y gestión de repartidores."""

    list_display = ("apellido", "nombre", "dni", "telefono", "mail", "tipo_vehiculo", "estado", "token")
    list_filter = ("estado", "tipo_vehiculo")      # filtros laterales
    search_fields = ("nombre", "apellido", "dni", "mail")
    readonly_fields = ("token",)                   # el token lo genera el sistema


@admin.register(Comercio)
class ComercioAdmin(admin.ModelAdmin):
    """Alta y gestión de comercios que despachan paquetes."""

    list_display = ("nombre", "telefono", "direccion")
    search_fields = ("nombre",)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    """Clientes (destinatarios): contacto y dirección de entrega."""

    list_display = ("dni", "telefono", "direccion", "paquetes_asociados")
    search_fields = ("dni", "direccion", "telefono")

    @admin.display(description="Paquetes")
    def paquetes_asociados(self, obj):
        """Cuántos paquetes apuntan a este cliente (FK `paquete.id_datos_cliente`)."""
        return obj.paquetes.count()



@admin.register(Paquete)
class PaqueteAdmin(admin.ModelAdmin):
    """Paquetes: el modelo central del sistema."""

    list_display = (
        "cod_seguimiento",
        "estado",
        "tamanio",
        "comercio",
        "cliente",
        "repartidor",
        "comprobante",
    )
    list_filter = ("estado", "tamanio", "comercio")
    search_fields = ("cod_seguimiento", "cliente__dni", "comercio__nombre")
    # En el formulario, estos campos se eligen con un buscador en vez de
    # un <select> con todos los registros (imprescindible con muchos datos):
    autocomplete_fields = ("cliente", "comercio", "repartidor")
    readonly_fields = ("cod_seguimiento",)         # lo genera el sistema


@admin.register(Comprobante)
class ComprobanteAdmin(admin.ModelAdmin):
    """Comprobantes de entrega (foto/PDF)."""

    # `file` es la columna del diagrama; se muestra la ruta relativa guardada.
    list_display = ("id", "file", "paquete")
    search_fields = ("id",)

