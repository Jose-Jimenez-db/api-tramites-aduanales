from rest_framework import status

from cobros.models import Cobro
from cuentas.pruebas import (
    PruebaAPI,
    crear_carga,
    crear_cliente,
    crear_cobro,
    crear_tipo_permiso,
    crear_tramite,
    crear_transportista,
)

from .models import PermisoTramite, Tramite

E = Tramite.Estado


class TramiteCRUDTests(PruebaAPI):
    URL = "/api/tramites/"

    def test_crear_tramite_genera_codigo_y_asigna_permisos_automaticos(self):
        """[CRUD][DECISIÓN AUTOMÁTICA] Crear -> 201, código TR-AAAA-NNNNN y permisos según tipo de carga."""
        crear_tipo_permiso("DUA", "TODAS")
        crear_tipo_permiso("SFE-FITO", "REFRIGERADA")
        crear_tipo_permiso("MINAE-SP", "PELIGROSA")
        carga = crear_carga(tipo="REFRIGERADA")
        self.como_operador()
        r = self.client.post(self.URL, {"carga": carga.id, "tipo": "IMPORTACION"})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertRegex(r.data["codigo"], r"^TR-\d{4}-\d{5}$")
        self.assertEqual(r.data["estado"], "REGISTRADO")
        codigos = sorted(p["codigo"] for p in r.data["permisos"])
        self.assertEqual(codigos, ["DUA", "SFE-FITO"])
        self.assertEqual(r.data["creado_por"], self.usuarios["Operador"].username)

    def test_eliminar_tramite_registrado(self):
        """[CRUD] Eliminar trámite REGISTRADO sin cobros -> 204 (sus permisos se borran en cascada)."""
        tramite = crear_tramite()
        self.como_admin()
        r = self.client.delete(f"{self.URL}{tramite.id}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PermisoTramite.objects.filter(tramite_id=tramite.id).exists())

    def test_listado_usa_select_y_prefetch_related(self):
        """[ORM] El listado hace un número fijo de consultas sin importar cuántos trámites haya."""
        for _ in range(5):
            tramite = crear_tramite(transportista=crear_transportista())
            crear_cobro(tramite)
        self.como_consulta()
        # auth (token + grupos) + count + trámites con JOIN + permisos + tipos de permiso + cobros
        with self.assertNumQueries(7):
            r = self.client.get(self.URL)
        self.assertEqual(r.data["total_registros"], 5)

    def test_filtros_combinados_estado_y_cliente(self):
        """[FILTRO] ?estado=EN_REVISION&cliente=<id> combina filtros por campo y por relación."""
        cliente = crear_cliente()
        crear_tramite(carga=crear_carga(cliente=cliente), estado=E.EN_REVISION)
        crear_tramite(carga=crear_carga(cliente=cliente), estado=E.REGISTRADO)
        crear_tramite(estado=E.EN_REVISION)
        self.como_consulta()
        r = self.client.get(self.URL, {"estado": "EN_REVISION", "cliente": cliente.id})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["total_registros"], 1)


class TramiteReglasTests(PruebaAPI):
    URL = "/api/tramites/"

    def cambiar(self, tramite, estado):
        return self.client.post(f"{self.URL}{tramite.id}/cambiar-estado/", {"estado": estado})

    def test_carga_con_tramite_activo_devuelve_409(self):
        """[REGLA RN-07] Segundo trámite activo para la misma carga -> 409."""
        carga = crear_carga()
        crear_tramite(carga=carga)
        self.como_operador()
        r = self.client.post(self.URL, {"carga": carga.id})
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

    def test_transportista_con_licencia_vencida_se_rechaza_en_patch(self):
        """[REGLA RN-08] PATCH con transportista de licencia vencida -> 400."""
        tramite = crear_tramite()
        vencido = crear_transportista(dias_licencia=-1)
        self.como_operador()
        r = self.client.patch(f"{self.URL}{tramite.id}/", {"transportista": vencido.id})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("transportista", r.data)
        tramite.refresh_from_db()
        self.assertIsNone(tramite.transportista_id)

    def test_transicion_de_estado_invalida_devuelve_400(self):
        """[REGLA RN-09] REGISTRADO -> LIBERADO no está permitido -> 400."""
        tramite = crear_tramite()
        self.como_operador()
        r = self.cambiar(tramite, "LIBERADO")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_se_aprueba_con_permisos_pendientes(self):
        """[REGLA RN-10] Aprobar con permisos pendientes -> 400."""
        tramite = crear_tramite(estado=E.EN_REVISION)
        self.como_operador()
        r = self.cambiar(tramite, "APROBADO")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("DUA", str(r.data))

    def test_no_se_libera_con_cobros_pendientes(self):
        """[REGLA RN-11] Liberar con un cobro pendiente -> 400."""
        tramite = crear_tramite(estado=E.APROBADO, transportista=crear_transportista())
        crear_cobro(tramite)
        self.como_operador()
        r = self.cambiar(tramite, "LIBERADO")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        tramite.refresh_from_db()
        self.assertEqual(tramite.estado, E.APROBADO)

    def test_tramite_liberado_no_se_modifica(self):
        """[REGLA RN-12] PATCH sobre trámite LIBERADO -> 409."""
        tramite = crear_tramite(estado=E.LIBERADO)
        self.como_operador()
        r = self.client.patch(f"{self.URL}{tramite.id}/", {"observaciones": "cambio"})
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

    def test_solo_se_eliminan_tramites_registrados(self):
        """[REGLA RN-12] Eliminar un trámite EN_REVISION -> 409."""
        tramite = crear_tramite(estado=E.EN_REVISION)
        self.como_admin()
        r = self.client.delete(f"{self.URL}{tramite.id}/")
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

    def test_aprobar_permiso_exige_numero_de_resolucion(self):
        """[REGLA RN-15] Aprobar un permiso sin número de resolución -> 400."""
        tramite = crear_tramite(estado=E.EN_REVISION)
        permiso = tramite.permisos_tramite.first()
        self.como_operador()
        r = self.client.post(
            f"{self.URL}{tramite.id}/resolver-permiso/", {"permiso": permiso.id, "estado": "APROBADO"}
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancelar_anula_cobros_pendientes(self):
        """[DECISIÓN AUTOMÁTICA] Al cancelar, los cobros pendientes pasan a ANULADO y los pagados se conservan."""
        tramite = crear_tramite(estado=E.EN_REVISION)
        pendiente = crear_cobro(tramite, concepto="ALMACENAJE")
        pagado = crear_cobro(tramite, concepto="HONORARIOS", estado=Cobro.Estado.PAGADO)
        self.como_operador()
        r = self.cambiar(tramite, "CANCELADO")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        pendiente.refresh_from_db()
        pagado.refresh_from_db()
        self.assertEqual(pendiente.estado, Cobro.Estado.ANULADO)
        self.assertEqual(pagado.estado, Cobro.Estado.PAGADO)


class TramiteFlujoCompletoTests(PruebaAPI):
    def test_flujo_de_registro_a_liberacion(self):
        """[FLUJO] Registrar -> revisar -> aprobar permiso -> aprobar -> cobrar -> pagar -> liberar."""
        crear_tipo_permiso("DUA", "TODAS")
        carga = crear_carga()
        transportista = crear_transportista()
        self.como_operador()

        r = self.client.post("/api/tramites/", {"carga": carga.id, "transportista": transportista.id})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        tid = r.data["id"]
        permiso_id = r.data["permisos"][0]["id"]

        r = self.client.post(f"/api/tramites/{tid}/cambiar-estado/", {"estado": "EN_REVISION"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        r = self.client.post(
            f"/api/tramites/{tid}/resolver-permiso/",
            {"permiso": permiso_id, "estado": "APROBADO", "numero_resolucion": "DGA-2026-001"},
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        r = self.client.post(f"/api/tramites/{tid}/cambiar-estado/", {"estado": "APROBADO"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        r = self.client.post("/api/cobros/", {"tramite": tid, "concepto": "HONORARIOS", "monto": "150000"})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        r = self.client.post(f"/api/cobros/{r.data['id']}/registrar-pago/", {"metodo_pago": "TRANSFERENCIA"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        r = self.client.post(f"/api/tramites/{tid}/cambiar-estado/", {"estado": "LIBERADO"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["estado"], "LIBERADO")
        self.assertIsNotNone(r.data["fecha_liberacion"])
        self.assertEqual(r.data["resumen_cobros"]["pendiente"], "0.00")


class TramitePermisosTests(PruebaAPI):
    def test_consulta_no_puede_cambiar_estado(self):
        """[PERMISO] Rol Consulta intenta cambiar estado -> 403."""
        tramite = crear_tramite()
        self.como_consulta()
        r = self.client.post(f"/api/tramites/{tramite.id}/cambiar-estado/", {"estado": "EN_REVISION"})
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_operador_no_modifica_catalogo_de_permisos(self):
        """[PERMISO] Solo el Administrador crea tipos de permiso -> 403 para Operador."""
        self.como_operador()
        r = self.client.post(
            "/api/tipos-permiso/", {"codigo": "X-1", "nombre": "X", "institucion": "Y", "aplica_a": "TODAS"}
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
