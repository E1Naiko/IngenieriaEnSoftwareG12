"""Pruebas de selección explícita de la base por entorno y del cableado de apps."""

from importlib import import_module
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase
from django.urls import get_resolver

from .settings import _configurar_db, _resolver_modo_db


class DatabaseModeTests(SimpleTestCase):
    def setUp(self):
        self.base_dir = Path("/proyecto/backend")

    def test_sin_modo_y_debug_activo_usa_sqlite_offline(self):
        modo = _resolver_modo_db({}, debug=True)
        bases = _configurar_db(modo, {}, self.base_dir)

        self.assertEqual(modo, "sqlite")
        self.assertEqual(bases["default"]["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(bases["default"]["NAME"], self.base_dir / "db.sqlite3")

    def test_ruta_sqlite_relativa_se_resuelve_desde_backend(self):
        bases = _configurar_db(
            "sqlite", {"DB_SQLITE_PATH": "data/dev.sqlite3"}, self.base_dir
        )

        self.assertEqual(
            bases["default"]["NAME"], self.base_dir / "data" / "dev.sqlite3"
        )

    def test_sqlite_explicita_no_usa_credenciales_postgres_presentes(self):
        bases = _configurar_db(
            "sqlite",
            {
                "DB_HOST": "supabase.example.com",
                "DB_NAME": "postgres",
                "DB_USER": "postgres.project",
                "DB_PASSWORD": "secret",
            },
            self.base_dir,
        )

        self.assertEqual(bases["default"]["ENGINE"], "django.db.backends.sqlite3")

    def test_produccion_por_defecto_exige_postgres_y_no_hace_fallback(self):
        modo = _resolver_modo_db({}, debug=False)

        self.assertEqual(modo, "postgres")
        with self.assertRaisesMessage(
            ImproperlyConfigured, "No se usa SQLite como fallback"
        ):
            _configurar_db(modo, {}, self.base_dir)

    def test_postgres_usa_supabase_y_ssl(self):
        bases = _configurar_db(
            "postgres",
            {
                "DB_HOST": "db.example.com",
                "DB_NAME": "postgres",
                "DB_USER": "postgres.project",
                "DB_PASSWORD": "secret",
            },
            self.base_dir,
        )

        self.assertEqual(bases["default"]["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(bases["default"]["HOST"], "db.example.com")
        self.assertEqual(bases["default"]["PORT"], "5432")
        self.assertEqual(bases["default"]["OPTIONS"], {"sslmode": "require"})

    def test_credenciales_de_plantilla_no_se_aceptan_en_produccion(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "DB_HOST"):
            _configurar_db(
                "postgres",
                {
                    "DB_HOST": "aws-0-<region>.pooler.supabase.com",
                    "DB_NAME": "postgres",
                    "DB_USER": "postgres.<project-ref>",
                    "DB_PASSWORD": "<database-password>",
                },
                self.base_dir,
            )

    def test_modo_desconocido_falla_con_mensaje_claro(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "DATABASE_MODE"):
            _resolver_modo_db({"DATABASE_MODE": "dockerhub"}, debug=True)


class CableadoDeAppsTests(SimpleTestCase):
    """
    Una app nueva se registra en INSTALLED_APPS y se monta en config/urls.py.

    Si el código de una app existe pero nadie agrega ``"<app>"`` a
    INSTALLED_APPS y ``path("api/", include("<app>.urls"))`` al ROOT_URLCONF,
    Django no falla al arrancar: los tests sí fallan después con
    ``NoReverseMatch`` o 404 en los endpoints. Estos tests lo detectan antes.
    """

    @staticmethod
    def _apps_locales_con_urls():
        """Paquetes de Python dentro de backend/ que declaran sus propias rutas."""
        base_dir = Path(settings.BASE_DIR)
        apps_locales = []
        for ruta in sorted(base_dir.iterdir()):
            if not ruta.is_dir() or not (ruta / "__init__.py").exists():
                continue
            if ruta.name == "config":  # es el ROOT_URLCONF, no una app
                continue
            if (ruta / "urls.py").exists():
                apps_locales.append(ruta.name)
        return apps_locales

    @staticmethod
    def _urlconfs_montados():
        """Módulos ``<app>.urls`` alcanzables desde el ROOT_URLCONF."""
        montados = set()
        pendientes = [get_resolver()]
        while pendientes:
            resolver = pendientes.pop()
            for patron in resolver.url_patterns:
                if not hasattr(patron, "url_patterns"):
                    continue  # es una vista, no un include()
                # include() ya importa el módulo: urlconf_name puede ser el
                # módulo (lo normal) o el string que se le pasó.
                nombre = getattr(patron, "urlconf_name", None)
                if not isinstance(nombre, str):
                    nombre = getattr(nombre, "__name__", None)
                if nombre:
                    montados.add(nombre)
                pendientes.append(patron)
        return montados

    def test_hay_apps_locales_para_revisar(self):
        # Si el descubrimiento se rompe, los tests de abajo pasarían vacíos.
        self.assertIn("actualizacionEstado", self._apps_locales_con_urls())

    def test_toda_app_con_urls_esta_en_installed_apps(self):
        labels = {config.label for config in apps.get_app_configs()}
        for app in self._apps_locales_con_urls():
            with self.subTest(app=app):
                self.assertIn(app, labels, f"Falta '{app}' en INSTALLED_APPS.")

    def test_toda_app_con_urls_tiene_sus_rutas_montadas(self):
        montados = self._urlconfs_montados()
        for app in self._apps_locales_con_urls():
            with self.subTest(app=app):
                self.assertIn(
                    f"{app}.urls",
                    montados,
                    f'Falta path("api/", include("{app}.urls")) en config/urls.py.',
                )

    def test_cada_nombre_de_ruta_de_las_apps_se_puede_reversar(self):
        nombres_montados = set(get_resolver().reverse_dict.keys())
        for app in self._apps_locales_con_urls():
            modulo = import_module(f"{app}.urls")
            for patron in modulo.urlpatterns:
                nombre = getattr(patron, "name", None)
                if not nombre:
                    continue
                with self.subTest(app=app, ruta=nombre):
                    self.assertIn(
                        nombre,
                        nombres_montados,
                        f"reverse('{nombre}') no se resuelve desde config/urls.py.",
                    )
