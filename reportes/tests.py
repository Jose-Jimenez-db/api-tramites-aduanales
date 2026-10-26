from rest_framework import status

from cobros.models import Cobro
from core.pruebas import (
    PruebaAPI,
    crear_carga,
    crear_cliente,
    crear_cobro,
    crear_tramite,
    crear_transportista,
)
from tramites.models import Tramite


class ReportesTests(PruebaAPI):
    def test_resumen_por_cliente_suma_correctamente(self):
        """[ORM Q1] Agregación por cliente: anulados no cuentan, pendientes van al saldo."""
        cliente = crear_cliente()
        tramite = crear_tramite(carga=crear_carga(cliente=cliente), estado=Tramite.Estado.EN_REVISION)
        crear_cobro(tramite, concepto="ALMACENAJE", monto="1000", estado=Cobro.Estado.PAGADO)
        crear_cobro(tramite, concepto="HONORARIOS", monto="500")
        crear_cobro(tramite, concepto="IMPUESTOS", monto="9999", estado=Cobro.Estado.ANULADO)
        self.como_consulta()
        r = self.client.get("/api/reportes/resumen-clientes/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        fila = next(f for f in r.data if f["id"] == cliente.id)
        self.assertEqual(fila["total_facturado"], 1500)
        self.assertEqual(fila["saldo_pendiente"], 500)
        self.assertEqual(fila["tramites_activos"], 1)

    def test_listos_para_liberar(self):
        """[ORM Q3] Solo aparecen trámites aprobados, con transportista vigente y todo pagado."""
        listo = crear_tramite(estado=Tramite.Estado.APROBADO, transportista=crear_transportista())
        crear_cobro(listo, estado=Cobro.Estado.PAGADO)
        con_deuda = crear_tramite(estado=Tramite.Estado.APROBADO, transportista=crear_transportista())
        crear_cobro(con_deuda)
        self.como_consulta()
        r = self.client.get("/api/reportes/listos-para-liberar/")
        self.assertEqual(r.data["cantidad"], 1)
        self.assertEqual(r.data["tramites"][0]["id"], listo.id)

    def test_parametro_dias_invalido_devuelve_400(self):
        """[VALIDACIÓN] ?dias=0 en licencias por vencer -> 400."""
        self.como_consulta()
        r = self.client.get("/api/reportes/licencias-por-vencer/", {"dias": 0})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reportes_requieren_autenticacion(self):
        """[PERMISO] Reporte sin token -> 401."""
        r = self.client.get("/api/reportes/tramites-por-estado/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
