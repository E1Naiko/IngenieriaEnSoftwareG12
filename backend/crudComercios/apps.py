"""
Configuración de la app crudComercios.

Registrada en ``INSTALLED_APPS`` como ``"crudComercios"`` (ver
``config/settings.py``). No define señales ni hooks de arranque;
su único propósito es darle a Django un ``AppConfig`` con nombre
y etiqueta estables para el sistema de migraciones y el admin.

Si en el futuro la app necesitara inicialización (p. ej. registrar
signals), hacerlo en ``ready()``.
"""

from django.apps import AppConfig


class CrudcomerciosConfig(AppConfig):
    """AppConfig para el CRUD de Comercios."""

    # Nombre Python del paquete (debe coincidir con el directorio).
    name = "crudComercios"

    # Etiqueta corta usada en la BD para permisos y contenttypes.
    # Se deja el default (crudComercios) para no romper migraciones
    # si alguien ya corrió el proyecto.
    # label = "crudComercios"

    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "CRUD Comercios"
