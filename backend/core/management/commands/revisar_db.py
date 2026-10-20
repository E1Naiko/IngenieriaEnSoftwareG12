"""

Diagnóstico de la base de datos (solo lectura).

Sirve cuando ``python manage.py migrate`` falla con errores del tipo
``relation "cliente" already exists``: la base ya tiene tablas de un
esquema anterior y las migraciones actuales intentan crearlas de nuevo.

Uso:
    python manage.py revisar_db

No modifica nada: compara las tablas que existen en la base con las que
esperan los modelos de ``core``, avisa si hay cambios de modelo sin
migración, informa cuántos datos hay y sugiere el próximo paso.
"""

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.questioner import NonInteractiveMigrationQuestioner
from django.db.migrations.state import ProjectState
from django.db.utils import OperationalError

SQL_BORRAR_TABLAS = """\
drop table if exists paquete, comprobante, cliente, comercio, repartidor cascade;"""

SQL_RECREAR = """\
drop schema public cascade;
create schema public;
grant all on schema public to postgres;
grant usage on schema public to anon, authenticated, service_role;
alter default privileges in schema public grant all on tables to postgres, anon, authenticated, service_role;
alter default privileges in schema public grant all on functions to postgres, anon, authenticated, service_role;
alter default privileges in schema public grant all on sequences to postgres, anon, authenticated, service_role;"""


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

        colisiones = []
        faltantes = []
        filas_por_tabla = {}

        for modelo in modelos:
            tabla = modelo._meta.db_table
            if tabla not in tablas:
                faltantes.append(modelo)
                self.stdout.write(f"  FALTA     {tabla}")
                continue

            columnas_reales = self._columnas(tabla)
            columnas_modelo = {campo.column for campo in modelo._meta.concrete_fields}
            filas = self._contar(tabla)
            filas_por_tabla[tabla] = filas

            if columnas_reales == columnas_modelo:
                self.stdout.write(f"  OK        {tabla} ({filas} fila(s))")
            else:
                colisiones.append(
                    (
                        tabla,
                        columnas_modelo - columnas_reales,
                        columnas_reales - columnas_modelo,
                    )
                )
                self.stdout.write(f"  DISTINTA  {tabla} ({filas} fila(s))")

        pendientes = self._cambios_sin_migracion()

        aplicadas = self._migraciones_core(tablas)
        self.stdout.write("")
        if aplicadas is None:
            self.stdout.write("Migraciones core aplicadas: (no existe la tabla django_migrations)")
        else:
            self.stdout.write(
                "Migraciones core aplicadas: " + (", ".join(aplicadas) if aplicadas else "(ninguna)")
            )

        if pendientes:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING("Cambios en los modelos sin migración:")
            )
            for operacion in pendientes:
                self.stdout.write(f"  - {operacion}")

        self._recomendar(colisiones, faltantes, aplicadas, filas_por_tabla, tablas, pendientes)

    # ------------------------------------------------------------------ utils

    def _cambios_sin_migracion(self):
        """Operaciones que makemigrations generaría todavía (drift de modelos)."""
        try:
            loader = MigrationLoader(None, ignore_no_migrations=True)
            autodetector = MigrationAutodetector(
                loader.project_state(),
                ProjectState.from_apps(apps),
                NonInteractiveMigrationQuestioner(specified_apps={"core"}, dry_run=True),
            )
            cambios = autodetector.changes(
                graph=loader.graph,
                trim_to_apps={"core"},
                convert_apps={"core"},
                migration_name="revisar_db",
            )
        except Exception as exc:  # nunca romper el diagnóstico por esto
            return [f"(no se pudo verificar: {exc})"]

        operaciones = []
        for migracion in cambios.get("core", []):
            operaciones.extend(operacion.describe() for operacion in migracion.operations)
        return operaciones

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
            cursor.execute(
                "SELECT name FROM django_migrations WHERE app = %s ORDER BY name", ["core"]
            )
            return [fila[0] for fila in cursor.fetchall()]

    def _resumen_datos(self, filas_por_tabla, tablas):
        """Cuenta lo que se perdería si se recrea el esquema. Devuelve el total de core."""
        total = sum(v for v in filas_por_tabla.values() if isinstance(v, int))
        usuarios = self._contar("auth_user") if "auth_user" in tablas else 0

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Datos que se perderían al recrear"))
        self.stdout.write(f"  Tablas de core: {total} fila(s)")
        self.stdout.write(f"  Usuarios de Django (auth_user): {usuarios} fila(s)")

        if total == 0:
            self.stdout.write(
                self.style.SUCCESS("  → No hay datos de la app que se pierdan.")
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"  → Hay {total} fila(s) en tablas de core: avisá antes de borrar."
                )
            )
        if total > 0 and isinstance(usuarios, int) and usuarios > 0:
            self.stdout.write(
                self.style.WARNING(
                    "  → Se van a borrar los usuarios: después hay que correr "
                    "'createsuperuser'."
                )
            )
        return total

    def _recomendar(self, colisiones, faltantes, aplicadas, filas_por_tabla, tablas, pendientes):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Diagnóstico"))

        if not faltantes and not colisiones and aplicadas and not pendientes:
            self.stdout.write(
                self.style.SUCCESS("Todo en orden: las tablas coinciden con los modelos.")
            )
            return

        if pendientes and not faltantes and not colisiones and aplicadas:
            self.stdout.write(
                self.style.WARNING(
                    "Las tablas de la base están bien, pero hay cambios en los modelos\n"
                    "sin migración (los de arriba): no se van a aplicar todavía. Corré:\n\n"
                    "    python manage.py makemigrations core\n"
                    "    python manage.py migrate\n"
                )
            )
            return

        if not colisiones and not faltantes:
            self.stdout.write(
                "Las tablas y sus columnas ya están bien: solo falta registrar la\n"
                "migración. No se toca ningún dato:\n\n"
                "    python manage.py migrate --fake-initial\n"
            )
            return

        if not colisiones:
            self.stdout.write(
                "Las tablas de core no existen todavía: corré\n\n"
                "    python manage.py migrate\n"
            )
            return

        self.stdout.write(
            "La base tiene tablas de un esquema anterior y las migraciones actuales\n"
            "no están registradas. Por eso migrate intenta crearlas otra vez y falla\n"
            "con 'relation ... already exists'.\n"
        )
        self.stdout.write("Diferencias encontradas:")
        for tabla, faltan, sobran in colisiones:
            if faltan:
                self.stdout.write(f"  - {tabla}: faltan columnas {sorted(faltan)}")
            if sobran:
                self.stdout.write(f"  - {tabla}: sobran columnas {sorted(sobran)}")

        compatible = all(not faltan for _, faltan, _ in colisiones)

        if compatible:
            self.stdout.write(
                "\nLas columnas del modelo ya existen todas: alcanza con registrar la\n"
                "migración sin tocar los datos:\n\n"
                "    python manage.py migrate --fake-initial\n"
            )
            return

        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "'migrate --fake-initial' NO sirve en este caso: Django solo da la\n"
                "migración por aplicada si las tablas existen Y tienen las columnas\n"
                "de los AddField (acá falta cliente.comercio_id), así que vuelve a\n"
                "fallar con el mismo error.\n"
            )
        )

        filas_core = self._resumen_datos(filas_por_tabla, tablas)

        if not aplicadas:
            if filas_core == 0:
                self.stdout.write(
                    "\nComo las tablas de core están vacías, alcanza con borrar solo esas\n"
                    "tablas (se conservan auth, admin y tu usuario de /admin). En\n"
                    "Supabase → SQL Editor:\n"
                )
                self.stdout.write(self.style.SQL_KEYWORD(SQL_BORRAR_TABLAS))
                self.stdout.write(
                    "\nDespués, en la terminal:\n\n"
                    "    python manage.py migrate\n"
                    "    python manage.py revisar_db      # debería decir 'Todo en orden'\n"
                )
            else:
                self.stdout.write("\nPara recrear el esquema, en Supabase → SQL Editor:\n")
                self.stdout.write(self.style.SQL_KEYWORD(SQL_RECREAR))
                self.stdout.write(
                    "\nDespués, en la terminal:\n\n"
                    "    python manage.py migrate\n"
                    "    python manage.py createsuperuser   # si perdiste el usuario\n"
                )
