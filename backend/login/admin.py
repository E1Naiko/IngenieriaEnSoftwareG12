from django.contrib import admin

from .models import Cliente, Comercio, Comprobante, Paquete, Repartidor


@admin.register(Repartidor)
class RepartidorAdmin(admin.ModelAdmin):
    list_display = ("apellido", "nombre", "dni", "telefono", "mail", "tipo_vehiculo", "estado", "token")
    list_filter = ("estado", "tipo_vehiculo")
    search_fields = ("nombre", "apellido", "dni", "mail")
    readonly_fields = ("token",)


@admin.register(Comercio)
class ComercioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "telefono", "direccion")
    search_fields = ("nombre",)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("dni", "telefono", "direccion", "comercio")
    list_filter = ("comercio",)
    search_fields = ("dni", "direccion")


@admin.register(Paquete)
class PaqueteAdmin(admin.ModelAdmin):
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
    autocomplete_fields = ("cliente", "comercio", "repartidor")
    readonly_fields = ("cod_seguimiento",)


@admin.register(Comprobante)
class ComprobanteAdmin(admin.ModelAdmin):
    list_display = ("id", "archivo", "paquete")
    search_fields = ("id",)
