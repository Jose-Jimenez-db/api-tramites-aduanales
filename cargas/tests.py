from datetime import timedelta

from django.utils import timezone
from rest_framework import status

from cuentas.pruebas import PruebaAPI, crear_carga, crear_cliente, crear_tramite

from .models import Carga


# Qué hace: Se agrupan las pruebas del CRUD de cargas y de sus reglas.
# Qué usa: PruebaAPI como clase base.
# Cómo lo hace: URL es la ruta que usan todas las pruebas de esta clase.
class CargaCRUDTests(PruebaAPI):
    URL = "/api/cargas/"

    # Qué hace: Se crea un cliente antes de cada prueba para usarlo en las cargas.
    # Qué usa: crear_cliente.
    # Cómo lo hace: Se guarda el cliente en self.cliente.
    def setUp(self):
        self.cliente = crear_cliente()

    # Qué hace: Se devuelven datos válidos para crear una carga; la prueba puede cambiar alguno.
    # Qué usa: self.cliente, timezone y update().
    # Cómo lo hace: Se arma un diccionario correcto con fecha de arribo de hoy y se aplican los
    #     cambios que mande la prueba.
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

    # Qué hace: Se prueba crear una carga (201) y que venga el nombre del cliente.
    # Qué usa: como_operador y self.client.post.
    # Cómo lo hace: Se manda el POST y se revisa el 201 y que cliente_nombre sea el del cliente.
    def test_crear_carga(self):
        """[CRUD] Crear carga -> 201 e incluye el nombre del cliente."""
        self.como_operador()
        r = self.client.post(self.URL, self.datos())
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["cliente_nombre"], self.cliente.nombre)

    # Qué hace: Se prueba ver el detalle de una carga (200).
    # Qué usa: crear_carga, como_consulta y self.client.get.
    # Cómo lo hace: Se pide la carga por id y se revisa el 200 y el número de contenedor.
    def test_detalle_de_carga(self):
        """[CRUD] Detalle de una carga -> 200."""
        carga = crear_carga(cliente=self.cliente)
        self.como_consulta()
        r = self.client.get(f"{self.URL}{carga.id}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["numero_contenedor"], carga.numero_contenedor)

    # Qué hace: RN-02: se prueba que un contenedor mal escrito responda 400.
    # Qué usa: como_operador y self.client.post.
    # Cómo lo hace: Se manda msc-123 y se revisa el 400 con el campo numero_contenedor.
    def test_contenedor_con_formato_invalido_devuelve_400(self):
        """[REGLA RN-02] Contenedor fuera del formato ISO 6346 -> 400."""
        self.como_operador()
        r = self.client.post(self.URL, self.datos(numero_contenedor="msc-123"))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("numero_contenedor", r.data)

    # Qué hace: RN-02: se prueba que con PATCH tampoco se pueda poner un peso mayor a 30 480 kg.
    # Qué usa: crear_carga, self.client.patch y refresh_from_db.
    # Cómo lo hace: Se manda PATCH con 50 000 kg, se revisa el 400 y que el peso en la base de
    #     datos siga igual.
    def test_peso_invalido_tambien_se_rechaza_en_patch(self):
        """[REGLA RN-02] PATCH con peso mayor a 30 480 kg -> 400 (invariante en PATCH)."""
        carga = crear_carga(cliente=self.cliente)
        self.como_operador()
        r = self.client.patch(f"{self.URL}{carga.id}/", {"peso_kg": "50000"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        carga.refresh_from_db()
        self.assertEqual(str(carga.peso_kg), "10000.00")

    # Qué hace: RN-03: se prueba que una fecha de arribo futura responda 400.
    # Qué usa: timedelta y self.client.post.
    # Cómo lo hace: Se calcula la fecha de mañana con hoy + timedelta(days=1), se manda y se revisa
    #     el 400.
    def test_fecha_de_arribo_futura_devuelve_400(self):
        """[REGLA RN-03] Fecha de arribo en el futuro -> 400."""
        self.como_operador()
        manana = timezone.localdate() + timedelta(days=1)
        r = self.client.post(self.URL, self.datos(fecha_arribo=str(manana)))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fecha_arribo", r.data)

    # Qué hace: RN-04: se prueba que un cliente inactivo no pueda registrar cargas.
    # Qué usa: crear_cliente(activo=False) y self.client.post.
    # Cómo lo hace: Se crea un cliente inactivo, se intenta crear una carga para él y se revisa el
    #     400.
    def test_cliente_inactivo_no_registra_cargas(self):
        """[REGLA RN-04] Cliente inactivo -> 400."""
        inactivo = crear_cliente(activo=False)
        self.como_operador()
        r = self.client.post(self.URL, self.datos(cliente=inactivo.id))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cliente", r.data)

    # Qué hace: RN-06: se prueba que no se pueda cambiar el cliente de una carga con trámites.
    # Qué usa: crear_carga, crear_tramite, self.client.patch y refresh_from_db.
    # Cómo lo hace: Se crea una carga con un trámite, se intenta pasarla a otro cliente con PATCH y
    #     se revisa el 400 y que el cliente no cambió.
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


# Qué hace: Se agrupan las pruebas de filtros y orden de cargas.
# Qué usa: PruebaAPI como clase base.
# Cómo lo hace: Cada método test_ revisa un filtro o el ordenamiento.
class CargaFiltrosTests(PruebaAPI):
    URL = "/api/cargas/"

    # Qué hace: Se prueba que ?tipo= y ?peso_min= funcionen juntos.
    # Qué usa: crear_carga y self.client.get.
    # Cómo lo hace: Se crean 3 cargas y solo una es REFRIGERADA con más de 10 000 kg; debe salir
    #     solo esa.
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

    # Qué hace: Se prueba el filtro por relación ?cliente_cedula=.
    # Qué usa: crear_cliente, crear_carga y self.client.get.
    # Cómo lo hace: Se crean dos cargas de clientes distintos y se filtra por la cédula de uno;
    #     debe salir 1.
    def test_filtro_por_relacion_cedula_del_cliente(self):
        """[FILTRO POR RELACIÓN] ?cliente_cedula= busca a través de la FK."""
        cliente = crear_cliente(cedula_juridica="3-101-555555")
        crear_carga(cliente=cliente)
        crear_carga()
        self.como_consulta()
        r = self.client.get(self.URL, {"cliente_cedula": "3-101-555555"})
        self.assertEqual(r.data["total_registros"], 1)

    # Qué hace: Se prueba el orden ?ordenar=-peso_kg (de mayor a menor).
    # Qué usa: crear_carga y self.client.get.
    # Cómo lo hace: Se crean cargas de 100, 300 y 200 kg y deben venir en orden 300, 200, 100.
    def test_ordenamiento_por_peso(self):
        """[ORDENAMIENTO] ?ordenar=-peso_kg devuelve de mayor a menor."""
        crear_carga(peso_kg="100")
        crear_carga(peso_kg="300")
        crear_carga(peso_kg="200")
        self.como_consulta()
        r = self.client.get(self.URL, {"ordenar": "-peso_kg"})
        pesos = [fila["peso_kg"] for fila in r.data["resultados"]]
        self.assertEqual(pesos, ["300.00", "200.00", "100.00"])
