"""Datos ficticios opcionales; nunca se cargan como parte de migrate."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Repartidor


class Command(BaseCommand):
    help = "Crea 12 repartidores demo: un registro por vehículo y estado, sin sobrescribir datos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirmar-desarrollo", action="store_true",
            help="Confirma que la base configurada es de pruebas, no de producción.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["confirmar_desarrollo"]:
            raise CommandError(
                "Solo para pruebas. Verificá la base configurada y usá --confirmar-desarrollo."
            )
        creados = existentes = conflictos = 0
        for i, vehiculo in enumerate(Repartidor.TipoVehiculo):
            for j, estado in enumerate(Repartidor.Estado):
                indice = i * len(Repartidor.Estado) + j
                dni = 99001000 + indice
                mail = f"repartidor.demo.{indice}@example.invalid"
                repartidor, creado = Repartidor.objects.get_or_create(
                    dni=dni,
                    defaults={
                        "nombre": f"Demo {vehiculo.label}",
                        "apellido": f"Prueba {estado.label}",
                        "telefono": "0000000000",
                        "mail": mail,
                        "tipo_vehiculo": vehiculo,
                        "estado": estado,
                    },
                )
                if creado:
                    creados += 1
                elif repartidor.mail == mail:
                    existentes += 1
                else:
                    conflictos += 1
                    self.stderr.write(self.style.WARNING(
                        f"DNI {dni} ocupado por otro registro: se conserva sin cambios."
                    ))
        self.stdout.write(self.style.SUCCESS(
            f"Creados: {creados}. Demo existentes: {existentes}. Conflictos omitidos: {conflictos}."
        ))
