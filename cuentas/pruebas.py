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
from cuentas.permisos import ADMINISTRADOR, CONSULTA, OPERADOR
from tramites.models import PermisoTramite, TipoPermiso, Tramite
from transportistas.models import Transportista

Usuario = get_user_model()
_secuencia = count(1)


# Qué hace: Se devuelve un número distinto cada vez que se llama (1, 2, 3...).
# Qué usa: count de itertools.
# Cómo lo hace: Se usa el contador _secuencia para que cada dato de prueba tenga un número
#     diferente y no choquen las cédulas, correos o placas, que son únicos.
def siguiente():
    return next(_secuencia)


# Qué hace: Se crea un cliente de prueba con datos válidos.
# Qué usa: La función siguiente y el modelo Cliente.
# Cómo lo hace: Se arman datos válidos con un número distinto (cédula 3-101-000001, etc.). Si la
#     prueba manda algún dato, ese reemplaza al de por defecto. Después se guarda con
#     objects.create.
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


# Qué hace: Se crea un transportista de prueba. Se puede decir en cuántos días vence la licencia.
# Qué usa: La función siguiente, timedelta, timezone y el modelo Transportista.
# Cómo lo hace: La fecha de vencimiento se calcula como hoy más dias_licencia; si se manda un
#     número negativo la licencia queda vencida. Los demás datos se arman con un número distinto.
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


# Qué hace: Se crea una carga de prueba. Si no se manda cliente, se crea uno nuevo.
# Qué usa: La función siguiente, crear_cliente, Decimal, timedelta y el modelo Carga.
# Cómo lo hace: Se arma un contenedor con formato válido (TEST0000001), tipo SECA, 10 000 kg y una
#     fecha de arribo de hace 2 días. Lo que mande la prueba reemplaza esos valores.
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


# Qué hace: Se busca o se crea un tipo de permiso de prueba (por defecto el DUA).
# Qué usa: get_or_create y el modelo TipoPermiso.
# Cómo lo hace: Se busca por código y, si no existe, se crea con un nombre, una institución de
#     prueba y el tipo de carga al que aplica.
def crear_tipo_permiso(codigo="DUA", aplica_a="TODAS"):
    tipo, _ = TipoPermiso.objects.get_or_create(
        codigo=codigo,
        defaults={"nombre": f"Permiso {codigo}", "institucion": "Institución de prueba", "aplica_a": aplica_a},
    )
    return tipo


# Qué hace: Se crea un trámite de prueba en el estado que se pida, y por defecto con un permiso.
# Qué usa: crear_carga, crear_tipo_permiso y los modelos Tramite y PermisoTramite.
# Cómo lo hace: Se crea el trámite con la carga (o una nueva) y el estado. Si con_permiso es True
#     se le agrega un permiso DUA pendiente.
def crear_tramite(carga=None, estado=Tramite.Estado.REGISTRADO, con_permiso=True, **datos):
    tramite = Tramite.objects.create(carga=carga or crear_carga(), estado=estado, **datos)
    if con_permiso:
        PermisoTramite.objects.create(tramite=tramite, tipo_permiso=crear_tipo_permiso())
    return tramite


# Qué hace: Se crea un cobro de prueba para un trámite.
# Qué usa: Decimal y el modelo Cobro.
# Cómo lo hace: Por defecto es de honorarios por 100 000 colones; la prueba puede cambiar el
#     concepto, el monto o el estado.
def crear_cobro(tramite, concepto=Cobro.Concepto.HONORARIOS, monto="100000", **datos):
    return Cobro.objects.create(tramite=tramite, concepto=concepto, monto=Decimal(monto), **datos)


# Qué hace: Es la clase base de todas las pruebas: se crea un usuario por rol y se puede iniciar
#     sesión con cualquiera.
# Qué usa: APITestCase de DRF, el modelo de usuario, Group y Token.
# Cómo lo hace: Todas las clases de tests.py heredan de esta clase, así no se repite el código para
#     crear usuarios y tokens.
class PruebaAPI(APITestCase):
    # Qué hace: Se crean los 3 usuarios de prueba (uno por rol) una sola vez para toda la clase.
    # Qué usa: @classmethod, create_user y Group.objects.get_or_create.
    # Cómo lo hace: Por cada rol se crea un usuario (prueba_administrador, prueba_operador,
    #     prueba_consulta) sin contraseña, se le asigna su grupo y se guarda en el diccionario
    #     cls.usuarios.
    @classmethod
    def setUpTestData(cls):
        cls.usuarios = {}
        for rol in (ADMINISTRADOR, OPERADOR, CONSULTA):
            usuario = Usuario.objects.create_user(username=f"prueba_{rol.lower()}")
            grupo, _ = Group.objects.get_or_create(name=rol)
            usuario.groups.add(grupo)
            cls.usuarios[rol] = usuario

    # Qué hace: Se inicia sesión en las pruebas con el usuario del rol que se pida.
    # Qué usa: Token.objects.get_or_create y self.client.credentials.
    # Cómo lo hace: Se crea el token del usuario directamente (sin contraseña) y se pone en el
    #     encabezado Authorization de todas las solicitudes siguientes. Así no hay contraseñas
    #     escritas en el código.
    def autenticar(self, rol):
        token, _ = Token.objects.get_or_create(user=self.usuarios[rol])
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    # Qué hace: Se inicia sesión como Administrador.
    # Qué usa: La función autenticar.
    # Cómo lo hace: Se llama a autenticar con el rol ADMINISTRADOR.
    def como_admin(self):
        self.autenticar(ADMINISTRADOR)

    # Qué hace: Se inicia sesión como Operador.
    # Qué usa: La función autenticar.
    # Cómo lo hace: Se llama a autenticar con el rol OPERADOR.
    def como_operador(self):
        self.autenticar(OPERADOR)

    # Qué hace: Se inicia sesión como Consulta (solo lectura).
    # Qué usa: La función autenticar.
    # Cómo lo hace: Se llama a autenticar con el rol CONSULTA.
    def como_consulta(self):
        self.autenticar(CONSULTA)
