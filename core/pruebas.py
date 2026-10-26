"""
Utilidades compartidas por las pruebas automatizadas.

Cada prueba crea sus propios datos; no depende de "cargar_datos".
Los usuarios de prueba se autentican con un token creado directamente,
así que no hay contraseñas escritas en el código.
"""
from datetime import timedelta
from decimal import Decimal
from itertools import count

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from cargas.models import Carga
from clientes.models import Cliente
from cobros.models import Cobro
from core.permisos import ADMINISTRADOR, CONSULTA, OPERADOR
from tramites.models import PermisoTramite, TipoPermiso, Tramite
from transportistas.models import Transportista

Usuario = get_user_model()
_secuencia = count(1)


def siguiente():
    return next(_secuencia)


def crear_cliente(**datos):
    n = siguiente()
    valores = {
        "cedula_juridica": f"3-101-{n:06d}",
        "nombre": f"Cliente de prueba {n}",
        "correo": f"cliente{n}@prueba.test",
        "telefono": "2661-0000",
    }
    valores.update(datos)
    return Cliente.objects.create(**valores)


def crear_transportista(dias_licencia=365, **datos):
    n = siguiente()
    valores = {
        "cedula": f"1-{n:04d}-{n:04d}",
        "nombre": f"Transportista {n}",
        "telefono": "8888-0000",
        "numero_licencia": f"LIC-T{n}",
        "vencimiento_licencia": timezone.localdate() + timedelta(days=dias_licencia),
        "placa_cabezal": f"C-{n:06d}",
    }
    valores.update(datos)
    return Transportista.objects.create(**valores)


def crear_carga(cliente=None, **datos):
    n = siguiente()
    valores = {
        "numero_contenedor": f"TEST{n:07d}",
        "cliente": cliente or crear_cliente(),
        "descripcion": "Mercadería de prueba",
        "tipo": Carga.Tipo.SECA,
        "peso_kg": Decimal("10000.00"),
        "buque": "Buque de prueba",
        "fecha_arribo": timezone.localdate() - timedelta(days=2),
    }
    valores.update(datos)
    return Carga.objects.create(**valores)


def crear_tipo_permiso(codigo="DUA", aplica_a="TODAS"):
    tipo, _ = TipoPermiso.objects.get_or_create(
        codigo=codigo,
        defaults={"nombre": f"Permiso {codigo}", "institucion": "Institución de prueba", "aplica_a": aplica_a},
    )
    return tipo


def crear_tramite(carga=None, estado=Tramite.Estado.REGISTRADO, con_permiso=True, **datos):
    tramite = Tramite.objects.create(carga=carga or crear_carga(), estado=estado, **datos)
    if con_permiso:
        PermisoTramite.objects.create(tramite=tramite, tipo_permiso=crear_tipo_permiso())
    return tramite


def crear_cobro(tramite, concepto=Cobro.Concepto.HONORARIOS, monto="100000", **datos):
    return Cobro.objects.create(tramite=tramite, concepto=concepto, monto=Decimal(monto), **datos)


class PruebaAPI(APITestCase):
    """Clase base: crea un usuario por rol y permite autenticarse con uno."""

    @classmethod
    def setUpTestData(cls):
        cls.usuarios = {}
        for rol in (ADMINISTRADOR, OPERADOR, CONSULTA):
            usuario = Usuario.objects.create_user(username=f"prueba_{rol.lower()}")
            usuario.groups.add(Group.objects.get(name=rol))
            cls.usuarios[rol] = usuario

    def autenticar(self, rol):
        token, _ = Token.objects.get_or_create(user=self.usuarios[rol])
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def como_admin(self):
        self.autenticar(ADMINISTRADOR)

    def como_operador(self):
        self.autenticar(OPERADOR)

    def como_consulta(self):
        self.autenticar(CONSULTA)
