"""
Admin de crudComercios — sin registros propios.

El modelo ``Comercio`` se administra desde ``core.admin.ComercioAdmin``
(``list_display = (nombre, telefono, direccion)`` + búsqueda por nombre).
Registrarlo también aquí produciría ``AlreadyRegistered``.

Si en el futuro crudComercios necesitara una vista de admin propia
(p. ej. con filtros o acciones distintas), crear un ``ModelAdmin`` aquí
y **quitar** el registro de ``core`` o usar un proxy model.
"""

from django.contrib import admin  # noqa: F401  (import conservado para facilitar extensión)

# Register your models here.
# Intencionalmente vacío — ver docstring del módulo.
