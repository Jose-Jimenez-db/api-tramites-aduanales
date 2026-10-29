"""
Carga datos ficticios para demostrar la API.

    python manage.py cargar_datos

Crea:
  - 3 usuarios de prueba (uno por rol) con la clave de DEMO_PASSWORD (.env)
  - catálogo de tipos de permiso
  - clientes, transportistas, cargas, trámites y cobros de ejemplo

Se puede ejecutar varias veces: no duplica registros.
Todos los datos son inventados.
"""
import os
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from cargas.models import Carga
from clientes.models import Cliente
from cobros.models import Cobro
from tramites.models import PermisoTramite, TipoPermiso, Tramite
from transportistas.models import Transportista

Usuario = get_user_model()

USUARIOS = [
    ("admin_demo", "Administrador", "Ana", "Administradora"),
    ("operador_demo", "Operador", "Óscar", "Operador"),
    ("consulta_demo", "Consulta", "Carla", "Consulta"),
]

TIPOS_PERMISO = [
    ("DUA", "Declaración Única Aduanera", "Dirección General de Aduanas", "TODAS"),
    ("SFE-FITO", "Certificado fitosanitario", "Servicio Fitosanitario del Estado", "REFRIGERADA"),
    ("MS-SANIT", "Permiso sanitario de importación", "Ministerio de Salud", "REFRIGERADA"),
    ("MINAE-SP", "Autorización de sustancias peligrosas", "MINAE", "PELIGROSA"),
    ("BOMB-01", "Visto bueno de seguridad", "Cuerpo de Bomberos", "PELIGROSA"),
]

CLIENTES = [
    ("3-101-100001", "Importadora del Pacífico S.A.", "ventas@impopacifico.test", "2661-1001"),
    ("3-101-100002", "Frutas Tropicales de Esparza S.A.", "info@frutasesparza.test", "2635-2002"),
    ("3-101-100003", "Químicos Industriales CR S.A.", "contacto@quimicoscr.test", "2222-3003"),
    ("3-102-100004", "Repuestos El Puerto Ltda.", "repuestos@elpuerto.test", "2663-4004"),
]

TRANSPORTISTAS = [
    # cédula, nombre, teléfono, licencia, días para vencer, placa
    ("1-1111-1111", "Mario Rojas Vargas", "8888-1111", "LIC-1001", 400, "C-100001"),
    ("2-2222-2222", "Luis Solís Mora", "8888-2222", "LIC-1002", 200, "C-100002"),
    ("6-3333-3333", "Jorge Castro Arias", "8888-3333", "LIC-1003", 20, "C-100003"),
    ("6-4444-4444", "Pedro Jiménez Ulate", "8888-4444", "LIC-1004", -30, "C-100004"),
]

CARGAS = [
    # contenedor, índice cliente, descripción, tipo, peso, buque, días desde arribo
    ("MSCU1000001", 0, "Electrodomésticos", "SECA", "18500.00", "MSC Caldera", 10),
    ("MSCU1000002", 0, "Muebles de oficina", "SECA", "12000.00", "MSC Caldera", 8),
    ("MAEU2000001", 1, "Piña y melón congelado", "REFRIGERADA", "22000.00", "Maersk Pacífico", 5),
    ("MAEU2000002", 1, "Fresas congeladas", "REFRIGERADA", "15000.50", "Maersk Pacífico", 3),
    ("HLCU3000001", 2, "Solventes industriales", "PELIGROSA", "9000.00", "Hapag Lloyd Sur", 6),
    ("CMAU4000001", 3, "Repuestos automotrices", "SECA", "7500.00", "CMA Puntarenas", 2),
]


class Command(BaseCommand):
    help = "Crea usuarios de prueba y datos ficticios para la demostración."

    @transaction.atomic
    def handle(self, *args, **options):
        clave = os.getenv("DEMO_PASSWORD")
        if not clave:
            raise CommandError("Defina DEMO_PASSWORD en el archivo .env antes de cargar los datos.")

        hoy = timezone.localdate()

        # 1. Usuarios de prueba
        for username, rol, nombre, apellido in USUARIOS:
            usuario, creado = Usuario.objects.get_or_create(
                username=username,
                defaults={"first_name": nombre, "last_name": apellido, "email": f"{username}@aduana.test"},
            )
            if creado:
                usuario.set_password(clave)
                usuario.save()
            grupo, _ = Group.objects.get_or_create(name=rol)
            usuario.groups.set([grupo])

        admin = Usuario.objects.get(username="admin_demo")
        operador = Usuario.objects.get(username="operador_demo")

        # 2. Catálogo de permisos
        for codigo, nombre, institucion, aplica_a in TIPOS_PERMISO:
            TipoPermiso.objects.get_or_create(
                codigo=codigo,
                defaults={"nombre": nombre, "institucion": institucion, "aplica_a": aplica_a},
            )

        # 3. Clientes
        clientes = []
        for cedula, nombre, correo, telefono in CLIENTES:
            cliente, _ = Cliente.objects.get_or_create(
                cedula_juridica=cedula,
                defaults={"nombre": nombre, "correo": correo, "telefono": telefono, "direccion": "Puntarenas"},
            )
            clientes.append(cliente)

        # 4. Transportistas (uno con licencia vencida para probar la regla RN-08)
        transportistas = []
        for cedula, nombre, telefono, licencia, dias, placa in TRANSPORTISTAS:
            transportista, _ = Transportista.objects.get_or_create(
                cedula=cedula,
                defaults={
                    "nombre": nombre,
                    "telefono": telefono,
                    "numero_licencia": licencia,
                    "vencimiento_licencia": hoy + timedelta(days=dias),
                    "placa_cabezal": placa,
                },
            )
            transportistas.append(transportista)

        # 5. Cargas
        cargas = []
        for contenedor, i_cliente, descripcion, tipo, peso, buque, dias in CARGAS:
            carga, _ = Carga.objects.get_or_create(
                numero_contenedor=contenedor,
                defaults={
                    "cliente": clientes[i_cliente],
                    "descripcion": descripcion,
                    "tipo": tipo,
                    "peso_kg": Decimal(peso),
                    "buque": buque,
                    "fecha_arribo": hoy - timedelta(days=dias),
                },
            )
            cargas.append(carga)

        # 6. Trámites en distintos estados (solo si no existen todavía)
        if not Tramite.objects.exists():
            self._crear_tramites(cargas, transportistas, admin, operador)

        self.stdout.write(self.style.SUCCESS("Datos de demostración cargados correctamente."))
        self.stdout.write("Usuarios: admin_demo, operador_demo, consulta_demo (clave = DEMO_PASSWORD)")

    def _nuevo_tramite(self, carga, usuario, tipo=Tramite.Tipo.IMPORTACION):
        tramite = Tramite.objects.create(carga=carga, tipo=tipo, creado_por=usuario)
        permisos = TipoPermiso.objects.filter(activo=True, aplica_a__in=["TODAS", carga.tipo])
        PermisoTramite.objects.bulk_create(
            [PermisoTramite(tramite=tramite, tipo_permiso=p) for p in permisos]
        )
        return tramite

    def _aprobar_permisos(self, tramite):
        ahora = timezone.now()
        for i, permiso in enumerate(tramite.permisos_tramite.all(), start=1):
            permiso.estado = PermisoTramite.Estado.APROBADO
            permiso.numero_resolucion = f"RES-{tramite.pk}-{i}"
            permiso.fecha_resolucion = ahora
            permiso.save()

    def _crear_tramites(self, cargas, transportistas, admin, operador):
        ahora = timezone.now()
        E = Tramite.Estado

        # Trámite 1: liberado, con todo pagado
        t1 = self._nuevo_tramite(cargas[0], operador)
        self._aprobar_permisos(t1)
        t1.transportista = transportistas[0]
        t1.estado = E.LIBERADO
        t1.fecha_liberacion = ahora
        t1.save()
        for concepto, monto in (("ALMACENAJE", "85000"), ("HONORARIOS", "150000"), ("IMPUESTOS", "420000")):
            Cobro.objects.create(
                tramite=t1, concepto=concepto, monto=Decimal(monto),
                estado=Cobro.Estado.PAGADO, metodo_pago=Cobro.MetodoPago.TRANSFERENCIA,
                fecha_pago=ahora, registrado_por=operador,
            )

        # Trámite 2: aprobado y listo para liberar (todo pagado)
        t2 = self._nuevo_tramite(cargas[2], operador)
        self._aprobar_permisos(t2)
        t2.transportista = transportistas[1]
        t2.estado = E.APROBADO
        t2.save()
        for concepto, monto in (("ALMACENAJE", "60000"), ("HONORARIOS", "150000")):
            Cobro.objects.create(
                tramite=t2, concepto=concepto, monto=Decimal(monto),
                estado=Cobro.Estado.PAGADO, metodo_pago=Cobro.MetodoPago.EFECTIVO,
                fecha_pago=ahora, registrado_por=operador,
            )

        # Trámite 3: en revisión, con un cobro pendiente
        t3 = self._nuevo_tramite(cargas[4], admin)
        t3.estado = E.EN_REVISION
        t3.save()
        Cobro.objects.create(tramite=t3, concepto="HONORARIOS", monto=Decimal("175000"), registrado_por=admin)

        # Trámite 4: aprobado pero con cobro pendiente (no se puede liberar)
        t4 = self._nuevo_tramite(cargas[3], operador)
        self._aprobar_permisos(t4)
        t4.transportista = transportistas[2]
        t4.estado = E.APROBADO
        t4.save()
        Cobro.objects.create(tramite=t4, concepto="ALMACENAJE", monto=Decimal("45000"), registrado_por=operador)

        # Trámite 5: recién registrado (exportación)
        self._nuevo_tramite(cargas[5], operador, tipo=Tramite.Tipo.EXPORTACION)
