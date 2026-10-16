"""
Modelos del sistema de reparto de paquetes (app core).

Esquema adaptado del diagrama de la base (ver Info/DB.md). Las tablas usan
el nombre exacto del diagrama (repartidor, comercio, cliente, paquete,
comprobante) vía Meta.db_table, y las columnas que Django no puede nombrar
tal cual (claves foráneas y camelCase) usan db_column para conservar el
nombre del diagrama: id_repartidor_asignado, id_comercio,
id_datos_cliente, id_comprobante, tipoVehiculo, codSeguimiento y file.

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
    """
    Quien entrega los paquetes.

    Un repartidor puede tener muchos paquetes asignados (relación inversa:
    ``repartidor.paquetes.all()``) y se identifica por su DNI único.
    El ``token`` de 6 caracteres lo genera el sistema al crearlo.
    """

    class TipoVehiculo(models.TextChoices):
        """Medios de transporte que puede usar un repartidor."""

        MOTO = "moto", "Moto"
        AUTO = "auto", "Auto"
        CAMIONETA = "camioneta", "Camioneta"

    class Estado(models.TextChoices):
        """Estados posibles del repartidor dentro del sistema."""

        OPERATIVO = "Operativo", "operativo"
        NO_OPERATIVO = "No Operativo", "no operativo"

    # --- Datos personales -------------------------------------------------
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    dni = models.PositiveIntegerField(unique=True)  # integer(8) único
    telefono = models.CharField(max_length=16)      # varchar(16) del diagrama
    mail = models.EmailField(max_length=255)

    # --- Datos del rol ------------------------------------------------------
    tipo_vehiculo = models.CharField(
        max_length=255,
        choices=TipoVehiculo.choices,
        default=TipoVehiculo.MOTO,
        help_text="Medio de transporte que usa para repartir.",
    )
    estado = models.CharField(
        max_length=255,
        choices=Estado.choices,
        default=Estado.ACTIVO,
        help_text="Situación del repartidor (activo, inactivo o suspendido).",
    )
    token = models.CharField(
        max_length=6,
        unique=True,
        editable=False,
        help_text="Código de 6 caracteres autogenerado que identifica al repartidor.",
    )

    class Meta:
        db_table = "repartidor"            # nombre de tabla del diagrama
        verbose_name = "repartidor"
        ordering = ["apellido", "nombre"]  # orden por defecto en listados

    def __str__(self):
        return f"{self.apellido}, {self.nombre} ({self.estado})"

    def save(self, *args, **kwargs):
        # Genera el token una sola vez, antes del primer guardado.
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

    # --- Campos "REVISAR" del diagrama, resueltos como properties ----------
    @property
    def listado_id_pedidos_asignados(self):
        """IDs de los paquetes asignados actualmente."""
        return list(self.paquetes.values_list("id", flat=True))

    @property
    def historial_asociado(self):
        """Paquetes ya entregados por este repartidor."""
        return self.paquetes.filter(estado=Paquete.Estado.ENTREGADO)


class Cliente(models.Model):
    """
    Datos de contacto del destinatario de un paquete.

    Según el diagrama no guarda nombre/apellido: solo cómo contactarlo y
    dónde entregarle. Cada cliente pertenece a un comercio (id_comercio)
    y se identifica por su DNI único.
    """

    telefono = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255)  # dónde entregar los paquetes
    dni = models.PositiveIntegerField(unique=True)
    comercio = models.ForeignKey(
        "Comercio",
        on_delete=models.PROTECT,   # no se puede borrar un comercio con clientes
        related_name="clientes",
    )  # id_comercio del diagrama

    class Meta:
        db_table = "cliente"        # nombre de tabla del diagrama
        verbose_name = "cliente"
        ordering = ["dni"]

    def __str__(self):
        return f"Cliente {self.dni} ({self.comercio})"


class Comercio(models.Model):
    """
    Comercio que despacha paquetes.

    Del lado "envía" tiene clientes propios (cliente.id_comercio) y
    paquetes (paquete.id_comercio). El campo ``datos_cliente``
    (id_datos_cliente del diagrama) apunta a un cliente de contacto.

    Nota sobre el ciclo del diagrama: cliente.id_comercio y
    comercio.id_datos_cliente no pueden ser ambos obligatorios (nadie
    podría crearse primero). Se resolvió dejando ``datos_cliente``
    opcional: se crea comercio -> cliente -> se linkea. Ver Info/DB.md.
    """

    nombre = models.CharField(max_length=255)
    telefono = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255)
    datos_cliente = models.ForeignKey(
        "Cliente",
        on_delete=models.SET_NULL,  # si se borra el cliente, no se borra el comercio
        null=True,
        blank=True,
        related_name="+",           # sin relación inversa (no se usa desde Cliente)
    )  # id_datos_cliente del diagrama

    class Meta:
        db_table = "comercio"       # nombre de tabla del diagrama
        verbose_name = "comercio"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Paquete(models.Model):
    """
    La entrega: vincula repartidor (opcional), comercio, cliente y
    comprobante (opcional, uno a uno).

    El ``cod_seguimiento`` es único y lo genera el sistema al crearlo con
    el formato SRFR-XXXXXXXX. Nuevos paquetes arrancan en estado
    "pendiente"; el historial del repartidor sale de filtrar por estado.
    """

    class Estado(models.TextChoices):
        """Ciclo de vida del paquete."""

        PENDIENTE = "pendiente", "Pendiente"
        EN_CAMINO = "en_camino", "En camino"
        ENTREGADO = "entregado", "Entregado"
        CANCELADO = "cancelado", "Cancelado"

    class Tamanio(models.TextChoices):
        """Tamaño estimado del paquete."""

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
        on_delete=models.SET_NULL,  # si se borra el repartidor, el paquete queda sin asignar
        null=True,
        blank=True,
        related_name="paquetes",
    )  # id_repartidor_asignado (opcional: el paquete puede no estar asignado aún)
    comercio = models.ForeignKey(
        Comercio,
        on_delete=models.PROTECT,   # no se puede borrar un comercio con paquetes
        related_name="paquetes",
    )  # id_comercio
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,   # no se puede borrar un cliente con paquetes
        related_name="paquetes",
    )  # id_datos_cliente
    comprobante = models.OneToOneField(
        "Comprobante",
        on_delete=models.SET_NULL,  # si se borra el comprobante, el paquete no se toca
        null=True,
        blank=True,
        related_name="paquete",
    )  # id_comprobante (?>? uno a uno: se carga cuando se entrega)
    tamanio = models.CharField(
        max_length=255,
        choices=Tamanio.choices,
        default=Tamanio.CHICO,
    )
    cod_seguimiento = models.CharField(
        max_length=255,
        unique=True,
        editable=False,
        help_text="Código autogenerado (SRFR-XXXXXXXX) para seguir la entrega.",
    )

    class Meta:
        db_table = "paquete"        # nombre de tabla del diagrama
        verbose_name = "paquete"
        ordering = ["-id"]          # los más nuevos primero

    def __str__(self):
        return f"{self.cod_seguimiento} ({self.estado})"

    def save(self, *args, **kwargs):
        # Genera el código de seguimiento una sola vez, antes del primer guardado.
        if not self.cod_seguimiento:
            self.cod_seguimiento = self._generar_codigo()
        super().save(*args, **kwargs)

    def _generar_codigo(self):
        """Genera un código único con el formato SRFR-XXXXXXXX."""
        while True:
            codigo = f"SRFR-{secrets.token_hex(4).upper()}"
            if not Paquete.objects.filter(cod_seguimiento=codigo).exists():
                return codigo


class Comprobante(models.Model):
    """
    Archivo (foto/PDF) que acredita la entrega de un paquete.

    Se relaciona uno a uno con Paquete desde el lado del paquete
    (paquete.id_comprobante), así que acá no va ninguna FK.
    ``archivo`` es opcional según el diagrama.
    """

    archivo = models.FileField(
        upload_to="comprobantes/%Y/%m/",  # guarda en media/comprobantes/2026/10/...
        null=True,
        blank=True,
    )  # file del diagrama

    class Meta:
        db_table = "comprobante"    # nombre de tabla del diagrama
        verbose_name = "comprobante"
        verbose_name_plural = "comprobantes"

    def __str__(self):
        return f"Comprobante {self.id}"
