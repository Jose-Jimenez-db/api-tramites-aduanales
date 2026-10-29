from rest_framework import status

from cuentas.pruebas import PruebaAPI, crear_cobro, crear_tramite
from tramites.models import Tramite

from .models import Cobro


# Qué hace: Se agrupan las pruebas de cobros.
# Qué usa: PruebaAPI como clase base.
# Cómo lo hace: URL es la ruta que usan todas las pruebas de esta clase.
class CobroTests(PruebaAPI):
    URL = "/api/cobros/"

    # Qué hace: Se crea un trámite EN_REVISION antes de cada prueba para cobrarle.
    # Qué usa: crear_tramite.
    # Cómo lo hace: Se guarda en self.tramite.
    def setUp(self):
        self.tramite = crear_tramite(estado=Tramite.Estado.EN_REVISION)

    # Qué hace: Se prueba que al crear un cobro quede PENDIENTE y con número de factura automático.
    # Qué usa: como_operador, self.client.post y assertRegex.
    # Cómo lo hace: Se crea el cobro y se revisa el 201, el estado PENDIENTE y que la factura tenga
    #     el formato FAC-000000.
    def test_crear_cobro_genera_numero_de_factura(self):
        """[CRUD][DECISIÓN AUTOMÁTICA] Crear cobro -> 201, estado PENDIENTE y factura FAC-NNNNNN."""
        self.como_operador()
        r = self.client.post(self.URL, {"tramite": self.tramite.id, "concepto": "ALMACENAJE", "monto": "85000"})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["estado"], "PENDIENTE")
        self.assertRegex(r.data["numero_factura"], r"^FAC-\d{6}$")

    # Qué hace: RN-13: se prueba que un monto de 0 responda 400.
    # Qué usa: como_operador y self.client.post.
    # Cómo lo hace: Se manda monto 0 y se revisa el 400.
    def test_monto_cero_devuelve_400(self):
        """[REGLA RN-13] Monto 0 -> 400."""
        self.como_operador()
        r = self.client.post(self.URL, {"tramite": self.tramite.id, "concepto": "ALMACENAJE", "monto": "0"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    # Qué hace: RN-13: se prueba que no se puedan tener dos cobros vigentes del mismo concepto en
    #     un trámite.
    # Qué usa: crear_cobro y self.client.post.
    # Cómo lo hace: Se crea un cobro de ALMACENAJE y se intenta crear otro igual; debe dar 409.
    def test_concepto_duplicado_devuelve_409(self):
        """[REGLA RN-13] Dos cobros vigentes del mismo concepto en el mismo trámite -> 409."""
        crear_cobro(self.tramite, concepto="ALMACENAJE")
        self.como_operador()
        r = self.client.post(self.URL, {"tramite": self.tramite.id, "concepto": "ALMACENAJE", "monto": "1000"})
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

    # Qué hace: RN-13: se prueba que no se pueda cobrar en un trámite LIBERADO.
    # Qué usa: crear_tramite y self.client.post.
    # Cómo lo hace: Se crea un trámite liberado, se intenta cobrarle y se revisa el 400.
    def test_no_se_cobra_en_tramite_cerrado(self):
        """[REGLA RN-13] Cobro sobre un trámite LIBERADO -> 400."""
        cerrado = crear_tramite(estado=Tramite.Estado.LIBERADO)
        self.como_operador()
        r = self.client.post(self.URL, {"tramite": cerrado.id, "concepto": "ALMACENAJE", "monto": "1000"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    # Qué hace: Se prueba que registrar el pago cambie el estado y ponga la fecha de pago sola.
    # Qué usa: crear_cobro y self.client.post.
    # Cómo lo hace: Se registra el pago en efectivo y se revisa el 200, el estado PAGADO y que
    #     fecha_pago no esté vacía.
    def test_registrar_pago_asigna_fecha_y_metodo(self):
        """[DECISIÓN AUTOMÁTICA] Registrar pago -> 200, estado PAGADO y fecha de pago automática."""
        cobro = crear_cobro(self.tramite)
        self.como_operador()
        r = self.client.post(f"{self.URL}{cobro.id}/registrar-pago/", {"metodo_pago": "EFECTIVO"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["estado"], "PAGADO")
        self.assertIsNotNone(r.data["fecha_pago"])

    # Qué hace: RN-14: se prueba que un cobro PAGADO no se pueda editar con PATCH.
    # Qué usa: crear_cobro, self.client.patch y refresh_from_db.
    # Cómo lo hace: Se intenta cambiar el monto, se revisa el 409 y que el monto siga igual en la
    #     base de datos.
    def test_cobro_pagado_no_se_modifica_ni_con_patch(self):
        """[REGLA RN-14] PATCH sobre un cobro PAGADO -> 409."""
        cobro = crear_cobro(self.tramite, estado=Cobro.Estado.PAGADO)
        self.como_operador()
        r = self.client.patch(f"{self.URL}{cobro.id}/", {"monto": "1"})
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)
        cobro.refresh_from_db()
        self.assertEqual(str(cobro.monto), "100000.00")

    # Qué hace: Se prueba que el estado no se pueda cambiar mandándolo en un PATCH.
    # Qué usa: crear_cobro, self.client.patch y refresh_from_db.
    # Cómo lo hace: Se manda estado=PAGADO; responde 200 pero el estado sigue PENDIENTE, porque es
    #     de solo lectura.
    def test_estado_no_se_puede_cambiar_con_patch(self):
        """[INVARIANTE] El campo estado es de solo lectura: PATCH estado=PAGADO no lo cambia."""
        cobro = crear_cobro(self.tramite)
        self.como_operador()
        r = self.client.patch(f"{self.URL}{cobro.id}/", {"estado": "PAGADO"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        cobro.refresh_from_db()
        self.assertEqual(cobro.estado, Cobro.Estado.PENDIENTE)

    # Qué hace: Se prueba que solo el Administrador pueda anular cobros.
    # Qué usa: crear_cobro, como_operador, como_admin y self.client.post.
    # Cómo lo hace: Como Operador debe dar 403 y como Administrador 200.
    def test_solo_el_administrador_anula(self):
        """[PERMISO] Operador intenta anular -> 403; Administrador -> 200."""
        cobro = crear_cobro(self.tramite)
        self.como_operador()
        self.assertEqual(self.client.post(f"{self.URL}{cobro.id}/anular/").status_code, status.HTTP_403_FORBIDDEN)
        self.como_admin()
        self.assertEqual(self.client.post(f"{self.URL}{cobro.id}/anular/").status_code, status.HTTP_200_OK)

    # Qué hace: Se prueba la paginación junto con el filtro ?estado=.
    # Qué usa: crear_tramite, crear_cobro y self.client.get.
    # Cómo lo hace: Se crean 6 cobros pendientes y 1 pagado. Con ?estado=PENDIENTE&page=2 debe
    #     salir 6 en total, 1 resultado en la página 2 y 2 páginas.
    def test_paginacion_y_filtro_por_estado(self):
        """[PAGINACIÓN][FILTRO] ?estado=PENDIENTE&page=2 (5 cobros por página)."""
        otro = crear_tramite(estado=Tramite.Estado.EN_REVISION)
        for concepto in ("ALMACENAJE", "DESALMACENAJE", "TRANSPORTE", "IMPUESTOS"):
            crear_cobro(self.tramite, concepto=concepto)
        for concepto in ("ALMACENAJE", "TRANSPORTE"):
            crear_cobro(otro, concepto=concepto)
        crear_cobro(self.tramite, concepto="HONORARIOS", estado=Cobro.Estado.PAGADO)
        self.como_consulta()
        r = self.client.get(self.URL, {"estado": "PENDIENTE", "page": 2})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["total_registros"], 6)
        self.assertEqual(len(r.data["resultados"]), 1)
        self.assertEqual(r.data["pagina_actual"], 2)
        self.assertEqual(r.data["total_paginas"], 2)
