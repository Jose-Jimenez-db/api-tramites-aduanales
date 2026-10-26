from rest_framework import status

from core.pruebas import PruebaAPI, crear_cobro, crear_tramite
from tramites.models import Tramite

from .models import Cobro


class CobroTests(PruebaAPI):
    URL = "/api/cobros/"

    def setUp(self):
        self.tramite = crear_tramite(estado=Tramite.Estado.EN_REVISION)

    def test_crear_cobro_genera_numero_de_factura(self):
        """[CRUD][DECISIÓN AUTOMÁTICA] Crear cobro -> 201, estado PENDIENTE y factura FAC-NNNNNN."""
        self.como_operador()
        r = self.client.post(self.URL, {"tramite": self.tramite.id, "concepto": "ALMACENAJE", "monto": "85000"})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["estado"], "PENDIENTE")
        self.assertRegex(r.data["numero_factura"], r"^FAC-\d{6}$")

    def test_monto_cero_devuelve_400(self):
        """[REGLA RN-13] Monto 0 -> 400."""
        self.como_operador()
        r = self.client.post(self.URL, {"tramite": self.tramite.id, "concepto": "ALMACENAJE", "monto": "0"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_concepto_duplicado_devuelve_409(self):
        """[REGLA RN-13] Dos cobros vigentes del mismo concepto en el mismo trámite -> 409."""
        crear_cobro(self.tramite, concepto="ALMACENAJE")
        self.como_operador()
        r = self.client.post(self.URL, {"tramite": self.tramite.id, "concepto": "ALMACENAJE", "monto": "1000"})
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

    def test_no_se_cobra_en_tramite_cerrado(self):
        """[REGLA RN-13] Cobro sobre un trámite LIBERADO -> 400."""
        cerrado = crear_tramite(estado=Tramite.Estado.LIBERADO)
        self.como_operador()
        r = self.client.post(self.URL, {"tramite": cerrado.id, "concepto": "ALMACENAJE", "monto": "1000"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registrar_pago_asigna_fecha_y_metodo(self):
        """[DECISIÓN AUTOMÁTICA] Registrar pago -> 200, estado PAGADO y fecha de pago automática."""
        cobro = crear_cobro(self.tramite)
        self.como_operador()
        r = self.client.post(f"{self.URL}{cobro.id}/registrar-pago/", {"metodo_pago": "EFECTIVO"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["estado"], "PAGADO")
        self.assertIsNotNone(r.data["fecha_pago"])

    def test_cobro_pagado_no_se_modifica_ni_con_patch(self):
        """[REGLA RN-14] PATCH sobre un cobro PAGADO -> 409."""
        cobro = crear_cobro(self.tramite, estado=Cobro.Estado.PAGADO)
        self.como_operador()
        r = self.client.patch(f"{self.URL}{cobro.id}/", {"monto": "1"})
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)
        cobro.refresh_from_db()
        self.assertEqual(str(cobro.monto), "100000.00")

    def test_estado_no_se_puede_cambiar_con_patch(self):
        """[INVARIANTE] El campo estado es de solo lectura: PATCH estado=PAGADO no lo cambia."""
        cobro = crear_cobro(self.tramite)
        self.como_operador()
        r = self.client.patch(f"{self.URL}{cobro.id}/", {"estado": "PAGADO"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        cobro.refresh_from_db()
        self.assertEqual(cobro.estado, Cobro.Estado.PENDIENTE)

    def test_solo_el_administrador_anula(self):
        """[PERMISO] Operador intenta anular -> 403; Administrador -> 200."""
        cobro = crear_cobro(self.tramite)
        self.como_operador()
        self.assertEqual(self.client.post(f"{self.URL}{cobro.id}/anular/").status_code, status.HTTP_403_FORBIDDEN)
        self.como_admin()
        self.assertEqual(self.client.post(f"{self.URL}{cobro.id}/anular/").status_code, status.HTTP_200_OK)

    def test_paginacion_y_filtro_por_estado(self):
        """[PAGINACIÓN][FILTRO] ?estado=PENDIENTE&tamano=2&pagina=2."""
        for concepto in ("ALMACENAJE", "DESALMACENAJE", "TRANSPORTE"):
            crear_cobro(self.tramite, concepto=concepto)
        crear_cobro(self.tramite, concepto="HONORARIOS", estado=Cobro.Estado.PAGADO)
        self.como_consulta()
        r = self.client.get(self.URL, {"estado": "PENDIENTE", "tamano": 2, "pagina": 2})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(len(r.data["results"]), 1)
        self.assertIsNone(r.data["next"])
