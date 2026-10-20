"""

Diagnóstico de la base de datos (solo lectura).

Sirve cuando ``python manage.py migrate`` falla con errores del tipo
``relation "cliente" already exists``: la base ya tiene tablas de un
esquema anterior y las migraciones actuales intentan crearlas de nuevo.

Uso:
    python manage.py revisar_db

No modifica nada: compara las tablas que existen en la base con las que
esperan los modelos de ``core`` y sugiere el próximo paso.
"""

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = (
        "Muestra qué tablas de la app core existen en la base, si coinciden "
        "con los modelos y qué hacer si hay un esquema viejo."
    )

    def handle(self, *args, **options):
        config = connection.settings_dict
        motor = config["ENGINE"].rsplit(".", 1)[-1]
        destino = config["NAME"]
        if config.get("HOST"):
            destino = f"{config.get('USER')}@{config['HOST']}:{config.get('PORT')}/{destino}"

        self.stdout.write(f"Base de datos: {motor} — {destino}\n")

        try:
            tablas = set(connection.introspection.table_names())
        except OperationalError as exc:
            self.stderr.write(self.style.ERROR(f"No se pudo conectar: {exc}"))
            self.stdout.write(
                "\nRevisá DB_HOST / DB_USER / DB_PASSWORD en backend/.env "
                "(Supabase → Connect → Session pooler)."
            )
            return

        modelos = list(apps.get_app_config("core").get_models())
        esperadas = {modelo._meta.db_table for modelo in modelos}

        colisiones = []
        faltantes = []

        for modelo in modelos:
            tabla = modelo._meta.db_table
            existe = tabla in tablas
            if not existe:
                faltantes.append(modelo)
                self.stdout.write(f"  FALTA     {tabla}")
                continue

            columnas_reales = self._columnas(tabla)
            columnas_modelo = {
                campo.column for campo in modelo._meta.concrete_fields
            }
            coincide = columnas_reales == columnas_modelo

            filas = self._contar(tabla)
            detalle = f"{filas} fila(s)"
            if coincide:
                self.stdout.write(f"  OK        {tabla} ({detalle})")
            else:
                colisiones.append((tabla, columnas_modelo - columnas_reales, columnas_reales - columnas_modelo, filas))
                self.stdout.write(f"  DISTINTA  {tabla} ({detalle})")

        aplicadas = self._migraciones_core(tablas)
        self.stdout.write("")
        if aplicadas is None:
            self.stdout.write("Migraciones core aplicadas: (no existe la tabla django_migrations)")
        else:
            self.stdout.write(
                "Migraciones core aplicadas: " + (", ".join(aplicadas) if aplicadas else "(ninguna)")
            )

        self._recomendar(colisiones, faltantes, aplicadas, esperadas & tablas)

    # ------------------------------------------------------------------ utils

    def _columnas(self, tabla):
        with connection.cursor() as cursor:
            descripcion = connection.introspection.get_table_description(cursor, tabla)
        return {columna.name for columna in descripcion}

    def _contar(self, tabla):
        try:
            with connection.cursor() as cursor:
                cursor.execute(f'SELECT COUNT(*) FROM "{tabla}"')
                return cursor.fetchone()[0]
        except Exception:
            return "?"

    def _migraciones_core(self, tablas):
        if "django_migrations" not in tablas:
            return None
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM django_migrations WHERE app = %s ORDER BY name", ["core"])
            return [fila[0] for fila in cursor.fetchall()]

    def _recomendar(self, colisiones, faltantes, aplicadas, tablas_existentes):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Diagnóstico"))

        if not faltantes and not colisiones and aplicadas:
            self.stdout.write(self.style.SUCCESS("Todo en orden: las tablas coinciden con los modelos."))
            return

        if colisiones or (tablas_existentes and not aplicadas):
            self.stdout.write(
                "La base tiene tablas de un esquema anterior, y las migraciones\n"
                "actuales todavía no están registradas. Por eso migrate intenta\n"
                "crearlas otra vez y falla con 'relation ... already exists'.\n"
            )
            if colisiones:
                self.stdout.write("Diferencias encontradas:")
                for tabla, faltan, sobran, _ in colisiones:
                    if faltan:
                        self.stdout.write(f"  - {tabla}: faltan columnas {sorted(faltan)}")
                    if sobran:
                        self.stdout.write(f"  - {tabla}: sobran columnas {sorted(sobran)}")
                self.stdout.write("")
                self.stdout.write(
                    self.style.WARNING(
                        "Como la estructura NO coincide, 'migrate --fake-initial'\n"
                        "dejaría la base inconsistente. Conviene recrear el esquema."
                    )
                )
            else:
                self.stdout.write(
                    "La estructura de las tablas coincide con los modelos: podés\n"
                    "registrar las migraciones sin recrear nada con:\n\n"
                    "    python manage.py migrate --fake-initial\n"
                )
                return

            self.stdout.write(
                "\nSi no te importan los datos que hay en Supabase, en el SQL Editor\n"
                "del dashboard ejecutá:\n\n"
                "    drop schema public cascade;\n"
                "    create schema public;\n"
                "    grant all on schema public to postgres;\n"
                "    grant all on schema public to public;\n\n"
                "y después, en la terminal:\n\n"
                "    python manage.py migrate\n"
                "    python manage.py createsuperuser   # si todavía no tenés usuario\n"
            )
            return

        self.stdout.write(
            "Faltan tablas: corré 'python manage.py migrate' para crearlas."
        )
