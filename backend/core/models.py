"""
Modelos del sistema de reparto de paquetes (app core).

Cada modelo conserva el nombre de tabla del diagrama mediante ``Meta.db_table``.
Las claves primarias son enteros de 32 bits y las columnas FK de ``paquete``
usan los nombres explícitos del modelo actual:

    paquete.id_repartidor_asignado  →  repartidor.id   opcional  (SET_NULL)
    paquete.id_comercio             →  comercio.id     obligatorio (PROTECT)
    paquete.id_datos_cliente        →  cliente.id      obligatorio (PROTECT)
    paquete.id_comprobante          →  comprobante.id  opcional, 1 a 1 (SET_NULL)

``comercio`` y ``cliente`` no se referencian entre sí: el único punto donde
ambos aparecen juntos es ``paquete``, así que el vínculo se consulta ahí.

``repartidor.listado_id_pedidos_asignados`` y
``repartidor.historial_asociado`` no son columnas: son relaciones inversas
sobre ``paquete`` (ver las properties al final de ``Repartidor``).
"""

import secrets
import string

from django.db import models
from django.db.models.functions import Lower, Trim
from django.db.models.lookups import Exact


class Repartidor(models.Model):
    """
    Quien entrega los paquetes.

    Se identifica por su DNI (único) y recibe un ``token`` de 6 caracteres
    autogenerado. Puede tener muchos paquetes asignados, y eso se lee con la
    relación inversa ``repartidor.paquetes.all()``.
    """

    class TipoVehiculo(models.TextChoices):
        """Medios de transporte que puede usar un repartidor."""

        MOTO = "moto", "Moto"
        AUTO = "auto", "Auto"
        CAMIONETA = "camioneta", "Camioneta"
        CAMION = "camion", "Camión"

    class Estado(models.TextChoices):
        """Situación del repartidor dentro del sistema."""

        ACTIVO = "activo", "Activo"        # disponible para recibir paquetes
        INACTIVO = "inactivo", "Inactivo"  # temporalmente fuera de la flota
        BAJA = "baja", "Baja"              # baja definitiva (HU #25)

    # --- Datos personales -------------------------------------------------
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    dni = models.PositiveIntegerField(unique=True)  # integer(8) único
    telefono = models.CharField(max_length=16)      # varchar(16)
    mail = models.EmailField(max_length=255)

    # --- Datos del rol ------------------------------------------------------
    tipo_vehiculo = models.CharField(
        max_length=255,
        choices=TipoVehiculo.choices,
        default=TipoVehiculo.MOTO,
        help_text="Medio de transporte que usa para repartir.",
    )
    tamanio_maximo_nivel = models.GeneratedField(
        expression=models.Case(
            models.When(Exact(Lower(Trim(models.F("tipo_vehiculo"))), models.Value("moto")), then=models.Value(1)),
            models.When(Exact(Lower(Trim(models.F("tipo_vehiculo"))), models.Value("auto")), then=models.Value(2)),
            models.When(Exact(Lower(Trim(models.F("tipo_vehiculo"))), models.Value("camioneta")), then=models.Value(3)),
            models.When(Exact(Lower(Trim(models.F("tipo_vehiculo"))), models.Value("camion")), then=models.Value(3)),
            default=models.Value(None),
        ),
        output_field=models.IntegerField(),
        db_persist=True,
        null=True,
        help_text="Nivel del tamaño máximo transportable: 1 chico, 2 mediano, 3 grande.",
    )
    estado = models.CharField(
        max_length=255,
        choices=Estado.choices,
        default=Estado.ACTIVO,
        help_text="Situación del repartidor (activo, inactivo o baja).",
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
        # El token se genera una sola vez, antes del primer guardado.
        if not self.token:
            self.token = self._generar_token()
        super().save(*args, **kwargs)

    @staticmethod
    def _generar_token() -> str:
        """Genera un token único de 6 caracteres (A-Z, 0-9)."""
        alfabeto = string.ascii_uppercase + string.digits
        while True:
            token = "".join(secrets.choice(alfabeto) for _ in range(6))
            if not Repartidor.objects.filter(token=token).exists():
                return token

    # --- Paquetes del repartidor (relación inversa sobre Paquete) ----------
    @property
    def listado_id_pedidos_asignados(self):
        """IDs de los paquetes que tiene asignados ahora mismo."""
        return list(self.paquetes.values_list("id", flat=True))

    @property
    def historial_asociado(self):
        """Queryset de paquetes que ya entregó (estado ``entregado``)."""
        return self.paquetes.filter(estado__iexact=Paquete.Estado.ENTREGADO)


class Cliente(models.Model):
    """
    Datos personales y de contacto del destinatario de un paquete.

    Guarda ``nombre``, ``apellido``, cómo contactarlo (``telefono``) y dónde
    entregarle (``direccion``). Se identifica por su DNI, único.
    Los comercios con los que trabaja se ven por sus paquetes:
    ``cliente.paquetes.values_list("comercio", flat=True)``.
    """

    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    telefono = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255)  # dirección de entrega
    dni = models.PositiveIntegerField(unique=True)

    class Meta:
        db_table = "cliente"        # nombre de tabla del diagrama
        verbose_name = "cliente"
        ordering = ["dni"]

    def __str__(self):
        return f"{self.apellido}, {self.nombre} ({self.dni})"


class Comercio(models.Model):
    """
    Comercio que despacha paquetes.

    Tres datos de contacto: ``nombre``, ``telefono`` y ``direccion``. No
    tiene FK propias; los clientes y paquetes del comercio se consultan por
    ``comercio.paquetes.all()`` / ``comercio.paquetes.values_list("cliente")``.
    """

    nombre = models.CharField(max_length=255)
    telefono = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255)

    class Meta:
        db_table = "comercio"       # nombre de tabla del diagrama
        verbose_name = "comercio"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Paquete(models.Model):
    """
    La entrega. Es la tabla que une todo: un repartidor (opcional porque el
    paquete puede nacer sin asignar), un comercio que despacha, un cliente
    que recibe y un comprobante (opcional, uno a uno, se carga al entregar).

    Arranca en estado ``pendiente``; ``retirado`` es otra opción que debe
    asignarse explícitamente, sin transiciones automáticas. ``cod_seguimiento``
    se autogenera con el formato SRFR-XXXXXXXX. ``fecha_origen`` y
    ``fecha_destino`` son fechas obligatorias. El historial de un repartidor
    sale de filtrar los paquetes entregados, no de otra tabla.
    """

    class Estado(models.TextChoices):
        """Ciclo de vida del paquete."""

        RETIRADO = "retirado", "Retirado"
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
        on_delete=models.SET_NULL,  # sin repartidor: el paquete vuelve a estar sin asignar
        null=True,
        blank=True,
        db_column="id_repartidor_asignado",
        related_name="paquetes",
    )
    comercio = models.ForeignKey(
        Comercio,
        on_delete=models.PROTECT,   # no se puede borrar un comercio con paquetes
        db_column="id_comercio",
        related_name="paquetes",
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,   # no se puede borrar un cliente con paquetes
        db_column="id_datos_cliente",
        related_name="paquetes",
    )
    comprobante = models.OneToOneField(
        "Comprobante",
        on_delete=models.SET_NULL,  # se borra el comprobante, el paquete sigue en pie
        null=True,
        blank=True,
        db_column="id_comprobante",
        related_name="paquete",
    )
    tamanio = models.CharField(
        max_length=255,
        choices=Tamanio.choices,
        default=Tamanio.CHICO,
    )
    tamanio_nivel = models.GeneratedField(
        expression=models.Case(
            models.When(Exact(Lower(Trim(models.F("tamanio"))), models.Value("chico")), then=models.Value(1)),
            models.When(Exact(Lower(Trim(models.F("tamanio"))), models.Value("mediano")), then=models.Value(2)),
            models.When(Exact(Lower(Trim(models.F("tamanio"))), models.Value("grande")), then=models.Value(3)),
            default=models.Value(None),
        ),
        output_field=models.IntegerField(),
        db_persist=True,
        null=True,
        help_text="Nivel de tamaño: 1 chico, 2 mediano, 3 grande.",
    )
    cod_seguimiento = models.CharField(
        max_length=255,
        unique=True,
        editable=False,
        help_text="Código autogenerado (SRFR-XXXXXXXX) para seguir la entrega.",
    )
    fecha_origen = models.DateField()
    fecha_destino = models.DateField()

    class Meta:
        db_table = "paquete"        # nombre de tabla del diagrama
        verbose_name = "paquete"
        ordering = ["-id"]          # los más nuevos primero

    def __str__(self):
        return f"{self.cod_seguimiento} ({self.estado})"

    def save(self, *args, **kwargs):
        # El código de seguimiento se genera una sola vez, antes del primer guardado.
        if not self.cod_seguimiento:
            self.cod_seguimiento = self._generar_codigo()
        super().save(*args, **kwargs)

    @staticmethod
    def _generar_codigo() -> str:
        """Genera un código único con el formato SRFR-XXXXXXXX."""
        while True:
            codigo = f"SRFR-{secrets.token_hex(4).upper()}"
            if not Paquete.objects.filter(cod_seguimiento=codigo).exists():
                return codigo


class Comprobante(models.Model):
    """
    Archivo (foto o PDF) que acredita la entrega de un paquete.

    La relación uno a uno la sostiene ``Paquete`` con su columna
    ``id_comprobante``, así que acá no hay ninguna FK: se accede al revés,
    ``comprobante.paquete``. ``file`` puede quedar vacío (``null``), que es el
    caso del comprobante creado antes de subir la foto.
    """

    file = models.FileField(
        max_length=255,
        upload_to="comprobantes/%Y/%m/",  # queda en media/comprobantes/2026/10/...
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "comprobante"    # nombre de tabla del diagrama
        verbose_name = "comprobante"
        verbose_name_plural = "comprobantes"

    def __str__(self):
        return f"Comprobante {self.id}"
