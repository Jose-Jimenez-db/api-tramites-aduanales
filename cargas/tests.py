from datetime import timedelta

from django.utils import timezone
from rest_framework import status

from cuentas.pruebas import PruebaAPI, crear_carga, crear_cliente, crear_tramite

from .models import Carga


class CargaCRUDTests(PruebaAPI):
    URL = "/api/cargas/"

    def setUp(self):
        self.cliente = crear_cliente()

    def datos(self, **cambios):
        datos = {
            "numero_contenedor": "MSCU7654321",
            "cliente": self.cliente.id,
            "descripcion": "Llantas",
            "tipo": "SECA",
            "peso_kg": "12000.50",
            "buque": "MSC Caldera",
            "fecha_arribo": str(timezone.localdate()),
        }
        datos.update(cambios)
        return datos

    def test_crear_carga(self):
        """[CRUD] Crear carga -> 201 e incluye el nombre del cliente."""
        self.como_operador()
        r = self.client.post(self.URL, self.datos())
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["cliente_nombre"], self.cliente.nombre)

    def test_detalle_de_carga(self):
        """[CRUD] Detalle de una carga -> 200."""
        carga = crear_carga(cliente=self.cliente)
        self.como_consulta()
        r = self.client.get(f"{self.URL}{carga.id}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["numero_contenedor"], carga.numero_contenedor)

    def test_contenedor_con_formato_invalido_devuelve_400(self):
        """[REGLA RN-02] Contenedor fuera del formato ISO 6346 -> 400."""
        self.como_operador()
        r = self.client.post(self.URL, self.datos(numero_contenedor="msc-123"))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("numero_contenedor", r.data)

    def test_peso_invalido_tambien_se_rechaza_en_patch(self):
        """[REGLA RN-02] PATCH con peso mayor a 30 480 kg -> 400 (invariante en PATCH)."""
        carga = crear_carga(cliente=self.cliente)
        self.como_operador()
        r = self.client.patch(f"{self.URL}{carga.id}/", {"peso_kg": "50000"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        carga.refresh_from_db()
        self.assertEqual(str(carga.peso_kg), "10000.00")

    def test_fecha_de_arribo_futura_devuelve_400(self):
        """[REGLA RN-03] Fecha de arribo en el futuro -> 400."""
        self.como_operador()
        manana = timezone.localdate() + timedelta(days=1)
        r = self.client.post(self.URL, self.datos(fecha_arribo=str(manana)))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fecha_arribo", r.data)

    def test_cliente_inactivo_no_registra_cargas(self):
        """[REGLA RN-04] Cliente inactivo -> 400."""
        inactivo = crear_cliente(activo=False)
        self.como_operador()
        r = self.client.post(self.URL, self.datos(cliente=inactivo.id))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cliente", r.data)

    def test_no_se_cambia_el_cliente_de_una_carga_con_tramites(self):
        """[REGLA RN-06] PATCH cliente en carga con trámites -> 400."""
        carga = crear_carga(cliente=self.cliente)
        crear_tramite(carga=carga)
        otro = crear_cliente()
        self.como_operador()
        r = self.client.patch(f"{self.URL}{carga.id}/", {"cliente": otro.id})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        carga.refresh_from_db()
        self.assertEqual(carga.cliente_id, self.cliente.id)


class CargaFiltrosTests(PruebaAPI):
    URL = "/api/cargas/"

    def test_filtros_combinados_tipo_y_peso(self):
        """[FILTRO] ?tipo=REFRIGERADA&peso_min=10000 combina filtros."""
        cliente = crear_cliente()
        crear_carga(cliente=cliente, tipo=Carga.Tipo.REFRIGERADA, peso_kg="15000")
        crear_carga(cliente=cliente, tipo=Carga.Tipo.REFRIGERADA, peso_kg="5000")
        crear_carga(cliente=cliente, tipo=Carga.Tipo.SECA, peso_kg="15000")
        self.como_consulta()
        r = self.client.get(self.URL, {"tipo": "REFRIGERADA", "peso_min": "10000"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["total_registros"], 1)

    def test_filtro_por_relacion_cedula_del_cliente(self):
        """[FILTRO POR RELACIÓN] ?cliente_cedula= busca a través de la FK."""
        cliente = crear_cliente(cedula_juridica="3-101-555555")
        crear_carga(cliente=cliente)
        crear_carga()
        self.como_consulta()
        r = self.client.get(self.URL, {"cliente_cedula": "3-101-555555"})
        self.assertEqual(r.data["total_registros"], 1)

    def test_ordenamiento_por_peso(self):
        """[ORDENAMIENTO] ?ordenar=-peso_kg devuelve de mayor a menor."""
        crear_carga(peso_kg="100")
        crear_carga(peso_kg="300")
        crear_carga(peso_kg="200")
        self.como_consulta()
        r = self.client.get(self.URL, {"ordenar": "-peso_kg"})
        pesos = [fila["peso_kg"] for fila in r.data["resultados"]]
        self.assertEqual(pesos, ["300.00", "200.00", "100.00"])
