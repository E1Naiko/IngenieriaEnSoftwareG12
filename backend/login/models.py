"""
Modelos del sistema de reparto de paquetes (app login).

Esquema adaptado del diagrama de la base (ver Info/DB.md). Las tablas usan
el nombre exacto del diagrama (repartidor, comercio, cliente, paquete,
comprobante) vía Meta.db_table.

Relaciones del diagrama:
- paquete.id_repartidor_asignado ?> repartidor   (muchos paquetes -> un repartidor)
- paquete.id_comercio          ?> comercio       (muchos paquetes -> un comercio)
- paquete.id_datos_cliente     ?> cliente        (muchos paquetes -> un cliente)
- paquete.id_comprobante       ?>? comprobante   (uno a uno)
- comercio.id_datos_cliente    ?> cliente
- cliente.id_comercio          ?> comercio

Los campos "listado_id_pedidos_asignados" e "historial_asociado" del
diagrama NO son columnas: se resuelven con la relación inversa
(repartidor.paquetes.all()) y consultas por estado. Ver Info/DB.md.
"""

import secrets
import string

from django.db import models


class Repartidor(models.Model):
    """Quien entrega los paquetes."""

    class TipoVehiculo(models.TextChoices):
        MOTO = "moto", "Moto"
        AUTO = "auto", "Auto"
        CAMIONETA = "camioneta", "Camioneta"
        BICICLETA = "bicicleta", "Bicicleta"
        A_PIE = "a_pie", "A pie"

    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"
        SUSPENDIDO = "suspendido", "Suspendido"

    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    dni = models.PositiveIntegerField(unique=True)  # integer(8) único
    telefono = models.CharField(max_length=16)
    mail = models.EmailField(max_length=255)
    tipo_vehiculo = models.CharField(
        max_length=255,
        choices=TipoVehiculo.choices,
        default=TipoVehiculo.MOTO,
    )
    estado = models.CharField(
        max_length=255,
        choices=Estado.choices,
        default=Estado.ACTIVO,
    )
    token = models.CharField(max_length=6, unique=True, editable=False)

    class Meta:
        db_table = "repartidor"
        verbose_name = "repartidor"
        ordering = ["apellido", "nombre"]

    def __str__(self):
        return f"{self.apellido}, {self.nombre} ({self.estado})"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self._generar_token()
        super().save(*args, **kwargs)

    def _generar_token(self):
        """Genera un token único de 6 caracteres (A-Z, 0-9)."""
        alfabeto = string.ascii_uppercase + string.digits
        while True:
            token = "".join(secrets.choice(alfabeto) for _ in range(6))
            if not Repartidor.objects.filter(token=token).exists():
                return token

    @property
    def listado_id_pedidos_asignados(self):
        """IDs de los paquetes asignados (resolución del campo REVISAR)."""
        return list(self.paquetes.values_list("id", flat=True))

    @property
    def historial_asociado(self):
        """Paquetes entregados del repartidor (resolución del campo REVISAR)."""
        return self.paquetes.filter(estado=Paquete.Estado.ENTREGADO)


class Cliente(models.Model):
    """Datos de contacto del destinatario, atado a un comercio."""

    telefono = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255)
    dni = models.PositiveIntegerField(unique=True)
    comercio = models.ForeignKey(
        "Comercio",
        on_delete=models.PROTECT,
        related_name="clientes",
    )  # id_comercio

    class Meta:
        db_table = "cliente"
        verbose_name = "cliente"
        ordering = ["dni"]

    def __str__(self):
        return f"Cliente {self.dni} ({self.comercio})"


class Comercio(models.Model):
    """Comercio que despacha paquetes."""

    nombre = models.CharField(max_length=255)
    telefono = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255)
    datos_cliente = models.ForeignKey(
        "Cliente",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )  # id_datos_cliente (nullable para romper el ciclo con cliente.id_comercio)

    class Meta:
        db_table = "comercio"
        verbose_name = "comercio"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Paquete(models.Model):
    """La entrega: vincula repartidor (opcional), comercio, cliente y comprobante."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_CAMINO = "en_camino", "En camino"
        ENTREGADO = "entregado", "Entregado"
        CANCELADO = "cancelado", "Cancelado"

    class Tamanio(models.TextChoices):
        CHICO = "chico", "Chico"
        MEDIANO = "mediano", "Mediano"
        GRANDE = "grande", "Grande"

    estado = models.CharField(
        max_length=255,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    repartidor = models.ForeignKey(
        Repartidor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paquetes",
    )  # id_repartidor_asignado
    comercio = models.ForeignKey(
        Comercio,
        on_delete=models.PROTECT,
        related_name="paquetes",
    )  # id_comercio
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="paquetes",
    )  # id_datos_cliente
    comprobante = models.OneToOneField(
        "Comprobante",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paquete",
    )  # id_comprobante
    tamanio = models.CharField(
        max_length=255,
        choices=Tamanio.choices,
        default=Tamanio.CHICO,
    )
    cod_seguimiento = models.CharField(max_length=255, unique=True, editable=False)

    class Meta:
        db_table = "paquete"
        verbose_name = "paquete"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.cod_seguimiento} ({self.estado})"

    def save(self, *args, **kwargs):
        if not self.cod_seguimiento:
            self.cod_seguimiento = self._generar_codigo()
        super().save(*args, **kwargs)

    def _generar_codigo(self):
        """Genera un código único con el formato LOGIN-XXXXXXXX."""
        while True:
            codigo = f"LOGIN-{secrets.token_hex(4).upper()}"
            if not Paquete.objects.filter(cod_seguimiento=codigo).exists():
                return codigo


class Comprobante(models.Model):
    """Archivo (foto/PDF) que acredita la entrega de un paquete."""

    archivo = models.FileField(upload_to="comprobantes/%Y/%m/", null=True, blank=True)  # file

    class Meta:
        db_table = "comprobante"
        verbose_name = "comprobante"
        verbose_name_plural = "comprobantes"

    def __str__(self):
        return f"Comprobante {self.id}"
