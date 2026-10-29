from rest_framework import status

from cobros.models import Cobro
from cuentas.pruebas import (
    PruebaAPI,
    crear_carga,
    crear_cliente,
    crear_cobro,
    crear_tramite,
    crear_transportista,
)
from tramites.models import Tramite


# Qué hace: Se agrupan las pruebas de los reportes.
# Qué usa: PruebaAPI como clase base.
# Cómo lo hace: Cada método test_ revisa una consulta o una validación de los reportes.
class ReportesTests(PruebaAPI):
    # Qué hace: Se prueba que la consulta Q1 sume bien: los anulados no cuentan y los pendientes
    #     van al saldo.
    # Qué usa: crear_cliente, crear_carga, crear_tramite, crear_cobro y self.client.get.
    # Cómo lo hace: Se crea un cliente con un cobro pagado de 1000, uno pendiente de 500 y uno
    #     anulado de 9999. Debe salir facturado 1500, saldo 500 y 1 trámite activo.
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

    # Qué hace: Se prueba que la consulta Q3 muestre solo los trámites que de verdad se pueden
    #     liberar.
    # Qué usa: crear_tramite, crear_transportista, crear_cobro y self.client.get.
    # Cómo lo hace: Se crean dos trámites aprobados, uno con todo pagado y otro con deuda. Debe
    #     salir solo el primero.
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

    # Qué hace: Se prueba que ?dias=0 en licencias por vencer responda 400.
    # Qué usa: como_consulta y self.client.get.
    # Cómo lo hace: Se manda dias=0 (tiene que ser de 1 a 365) y se revisa el 400.
    def test_parametro_dias_invalido_devuelve_400(self):
        """[VALIDACIÓN] ?dias=0 en licencias por vencer -> 400."""
        self.como_consulta()
        r = self.client.get("/api/reportes/licencias-por-vencer/", {"dias": 0})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    # Qué hace: Se prueba que los reportes no se puedan ver sin token (401).
    # Qué usa: self.client.get.
    # Cómo lo hace: Se pide un reporte sin iniciar sesión y se revisa el 401.
    def test_reportes_requieren_autenticacion(self):
        """[PERMISO] Reporte sin token -> 401."""
        r = self.client.get("/api/reportes/tramites-por-estado/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
