"""
Modelos de crudComercios — intencionalmente vacío.

Toda la definición de tablas vive en ``core.models`` (ver ``Info/DB.md``).
El modelo ``Comercio`` que manipula esta app está en ``core.models.Comercio``
y usa ``db_table = "comercio"`` para respetar el diagrama.

Razones para no duplicar el modelo aquí:

1. **Fuente única de verdad**: una sola clase = una sola tabla = una sola
   migración. Duplicar generaría dos tablas o conflictos de ``db_table``.
2. **Comercio ↔ cliente**: el vínculo directo se borró del esquema (el
   diagrama ya no tiene ``comercio.id_datos_cliente`` ni ``cliente.id_comercio``);
   la relación se infiere por ``Paquete``. Ver ``Info/DB.md``.
3. **Admin centralizado**: ``core.admin.ComercioAdmin`` ya registra el modelo.

Si se necesita lógica exclusiva del CRUD (managers, querysets), crear
un *proxy model* o un *manager* en este módulo en vez de redefinir la tabla:

    from core.models import Comercio as CoreComercio

    class Comercio(CoreComercio):
        class Meta:
            proxy = True
"""

# Este archivo se deja vacío a propósito — ver docstring del módulo.
from django.db import models  # noqa: F401  (importado para que ``makemigrations`` no falle si se agrega un proxy)
