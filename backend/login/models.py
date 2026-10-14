"""
Modelos del sistema de reparto de paquetes (app login).

Relaciones:
- Un paquete pertenece a un comercio y a un cliente, y tiene a lo sumo
  un repartidor asignado (uno a muchos: repartidor.paquetes.all()).
- Un paquete tiene a lo sumo un comprobante (foto/PDF de la entrega).
"""

import secrets

from django.db import models


class Repartidor(models.Model):
    """Quien entrega los paquetes."""

    class TipoVehiculo(models.TextChoices):
        MOTO = "moto", "Moto"
        AUTO = "auto", "Auto"
        CAMIONETA = "camioneta", "Camioneta"
        BICICLETA = "bicicleta", "Bicicleta"
        A_PIE = "a_pie", "A pie"

    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    dni = models.PositiveIntegerField(unique=True)
    telefono = models.CharField(max_length=30, blank=True)
    tipo_vehiculo = models.CharField(
        max_length=20,
        choices=TipoVehiculo.choices,
        default=TipoVehiculo.MOTO,
    )
    activo = models.BooleanField(default=True)
    fecha_alta = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "repartidor"
        ordering = ["apellido", "nombre"]

    def __str__(self):
        return f"{self.apellido}, {self.nombre}"

    @property
    def paquetes(self):
        """Paquetes asignados actualmente (relación inversa)."""
        return self.paquete_set.all()


class Comercio(models.Model):
    """Comercio que despacha paquetes."""

    nombre = models.CharField(max_length=150)
    cuit = models.CharField(max_length=13, unique=True)  # formato: 30-12345678-9
    direccion = models.CharField(max_length=200, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        verbose_name = "comercio"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Cliente(models.Model):
    """Destinatario del paquete."""

    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    dni = models.PositiveIntegerField(unique=True)
    direccion = models.CharField(max_length=200)
    telefono = models.CharField(max_length=30, blank=True)

    class Meta:
        verbose_name = "cliente"
        ordering = ["apellido", "nombre"]

    def __str__(self):
        return f"{self.apellido}, {self.nombre}"


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

    codigo_seguimiento = models.CharField(max_length=20, unique=True, editable=False)
    repartidor = models.ForeignKey(
        Repartidor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paquetes_asignados",
    )
    comercio = models.ForeignKey(Comercio, on_delete=models.PROTECT, related_name="paquetes")
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="paquetes")
    descripcion = models.CharField(max_length=200, blank=True)
    tamanio = models.CharField(
        max_length=10,
        choices=Tamanio.choices,
        default=Tamanio.CHICO,
    )
    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "paquete"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.codigo_seguimiento} ({self.estado})"

    def save(self, *args, **kwargs):
        if not self.codigo_seguimiento:
            self.codigo_seguimiento = self._generar_codigo()
        super().save(*args, **kwargs)

    def _generar_codigo(self):
        """Genera un código único con el formato LOGIN-XXXXXXXX."""
        while True:
            codigo = f"LOGIN-{secrets.token_hex(4).upper()}"
            if not Paquete.objects.filter(codigo_seguimiento=codigo).exists():
                return codigo


class Comprobante(models.Model):
    """Archivo (foto/PDF) que acredita la entrega de un paquete."""

    paquete = models.OneToOneField(Paquete, on_delete=models.CASCADE, related_name="comprobante")
    archivo = models.FileField(upload_to="comprobantes/%Y/%m/")
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "comprobante"
        verbose_name_plural = "comprobantes"

    def __str__(self):
        return f"Comprobante de {self.paquete.codigo_seguimiento}"
