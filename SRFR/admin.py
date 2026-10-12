from django.contrib import admin

from .models import Cliente, Comercio, Comprobante, Paquete, Repartidor


@admin.register(Repartidor)
class RepartidorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "telefono", "tipo_vehiculo", "estado")
    list_filter = ("tipo_vehiculo", "estado")
    search_fields = ("nombre", "telefono")


@admin.register(Comercio)
class ComercioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "telefono")
    search_fields = ("nombre",)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("dni", "telefono", "direccion")
    search_fields = ("dni", "direccion")


@admin.register(Comprobante)
class ComprobanteAdmin(admin.ModelAdmin):
    list_display = ("id", "archivo")


@admin.register(Paquete)
class PaqueteAdmin(admin.ModelAdmin):
    list_display = ("cod_seguimiento", "comercio", "cliente", "repartidor", "tamanio")
    list_filter = ("tamanio", "repartidor")
    search_fields = ("cod_seguimiento",)
    readonly_fields = ("cod_seguimiento",)
    autocomplete_fields = ("repartidor", "comercio", "cliente")
