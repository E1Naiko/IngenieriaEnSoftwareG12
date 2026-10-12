import uuid

from django.db import models


def generar_cod_seguimiento():
    """Genera un código de seguimiento corto y aleatorio, ej: 'SRFR-3FA29D1E'."""
    return f"SRFR-{uuid.uuid4().hex[:8].upper()}"


class Repartidor(models.Model):
    """Repartidor del sistema.

    -> Sobre el diagrama (REVISAR):
    - `listado_id_pedidos_asignados` NO va como columna: en un modelo relacional
      esa "lista" se obtiene con la relación inversa. En Django:
          repartidor.paquetes.all()
      (ver el ForeignKey `repartidor` en el modelo Paquete).
    - `historial_asociado` tampoco es columna: el historial se deriva consultando
      los paquetes del repartidor, ej:
          repartidor.paquetes.filter(...)  # agregar un estado/filtro a futuro
    """

    class TipoVehiculo(models.TextChoices):
        MOTO = "MOTO", "Moto"
        AUTO = "AUTO", "Auto"
        CAMION = "CAMION", "Camión"
        BICICLETA = "BICICLETA", "Bicicleta"

    class Estado(models.TextChoices):
        LIBRE = "LIBRE", "Libre"
        OCUPADO = "OCUPADO", "Ocupado"

    nombre = models.CharField(max_length=255)
    telefono = models.CharField(max_length=255)
    # db_column mantiene el nombre de columna exacto de su diagrama (tipoVehiculo)
    tipo_vehiculo = models.CharField(
        "tipo de vehículo",
        max_length=255,
        choices=TipoVehiculo.choices,
        db_column="tipoVehiculo",
    )
    estado = models.CharField(
        max_length=255,
        choices=Estado.choices,
        default=Estado.LIBRE,
    )

    class Meta:
        db_table = "repartidor"
        verbose_name_plural = "repartidores"

    def __str__(self):
        return f"{self.nombre} ({self.get_estado_display()})"


class Comercio(models.Model):
    nombre = models.CharField(max_length=255)
    telefono = models.CharField(max_length=255)

    class Meta:
        db_table = "comercio"

    def __str__(self):
        return self.nombre


class Cliente(models.Model):
    """Datos del cliente que recibe el paquete.

    -> REVISAR: `dni` queda como entero positivo (en Argentina alcanza hasta
    ~99.999.999) y UNIQUE para no cargar dos veces a la misma persona.
    """

    telefono = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255)
    dni = models.PositiveIntegerField(unique=True)

    class Meta:
        db_table = "cliente"

    def __str__(self):
        return f"Cliente DNI {self.dni}"


class Comprobante(models.Model):
    """Comprobante (foto/PDF) de la entrega.

    -> REVISAR: el diagrama lo tenía como varchar; en Django se usa FileField,
    que guarda el archivo en MEDIA_ROOT/comprobantes/ y en la base queda la ruta.
    """

    archivo = models.FileField(
        upload_to="comprobantes/",
        blank=True,
        null=True,
        db_column="file",
    )

    class Meta:
        db_table = "comprobante"

    def __str__(self):
        return f"Comprobante #{self.pk}"


class Paquete(models.Model):
    """Paquete a entregar.

    Relaciones:
    - Un REPARTIDOR tiene muchos paquetes (o ninguno todavía) ->
      ForeignKey nullable. Si el repartidor se da de baja, los paquetes
      quedan sin asignar (SET_NULL), no se borran.
    - Un COMERCIO y un CLIENTE tienen muchos paquetes, y no deberían
      borrarse si tienen paquetes asociados -> PROTECT.
    - Un COMPROBANTE corresponde a un solo paquete -> OneToOneField,
      opcional hasta que se confirma la entrega.
    """

    class Tamanio(models.TextChoices):
        CHICO = "CHICO", "Chico"
        MEDIANO = "MEDIANO", "Mediano"
        GRANDE = "GRANDE", "Grande"

    repartidor = models.ForeignKey(
        Repartidor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paquetes",
        db_column="id_repartidor_asignado",
    )
    comercio = models.ForeignKey(
        Comercio,
        on_delete=models.PROTECT,
        related_name="paquetes",
        db_column="id_comercio",
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="paquetes",
        verbose_name="datos del cliente",
        db_column="id_datos_cliente",
    )
    comprobante = models.OneToOneField(
        Comprobante,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paquete",
        db_column="id_comprobante",
    )
    tamanio = models.CharField("tamaño", max_length=255, choices=Tamanio.choices)
    # REVISAR: el código es único y se autogenera (ej: SRFR-3FA29D1E);
    # editable=False para que nadie lo pise desde un formulario.
    cod_seguimiento = models.CharField(
        "código de seguimiento",
        max_length=255,
        unique=True,
        default=generar_cod_seguimiento,
        editable=False,
        db_column="codSeguimiento",
    )

    class Meta:
        db_table = "paquete"

    def __str__(self):
        return f"Paquete {self.cod_seguimiento}"
