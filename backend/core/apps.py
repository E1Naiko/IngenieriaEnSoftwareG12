from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuración de la app principal del proyecto."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Core — app principal"
