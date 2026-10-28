"""Pruebas de selección explícita de la base por entorno."""

from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

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
