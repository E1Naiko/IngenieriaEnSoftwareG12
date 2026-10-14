from django.contrib import admin

from .models import Cliente, Comercio, Comprobante, Paquete, Repartidor


@admin.register(Repartidor)
class RepartidorAdmin(admin.ModelAdmin):
    list_display = ("apellido", "nombre", "dni", "tipo_vehiculo", "activo")
    list_filter = ("activo", "tipo_vehiculo")
    search_fields = ("nombre", "apellido", "dni")


@admin.register(Comercio)
class ComercioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cuit", "telefono", "email")
    search_fields = ("nombre", "cuit")


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("apellido", "nombre", "dni", "direccion")
    search_fields = ("nombre", "apellido", "dni")


@admin.register(Paquete)
class PaqueteAdmin(admin.ModelAdmin):
    list_display = (
        "codigo_seguimiento",
        "comercio",
        "cliente",
        "repartidor",
        "estado",
        "tamanio",
        "fecha_creacion",
    )
    list_filter = ("estado", "tamanio", "comercio")
    search_fields = ("codigo_seguimiento", "cliente__apellido", "cliente__dni", "comercio__nombre")
    autocomplete_fields = ("cliente", "comercio", "repartidor")


@admin.register(Comprobante)
class ComprobanteAdmin(admin.ModelAdmin):
    list_display = ("paquete", "archivo", "fecha_subida")
    search_fields = ("paquete__codigo_seguimiento",)
