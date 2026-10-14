from django.apps import AppConfig


class LoginConfig(AppConfig):
    """Configuración de la app principal del proyecto."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "login"
    verbose_name = "Login — app principal"
