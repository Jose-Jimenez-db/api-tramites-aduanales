from rest_framework import status

from core.pruebas import PruebaAPI, crear_carga, crear_cliente, crear_tramite
from tramites.models import Tramite

from .models import Cliente


class ClienteCRUDTests(PruebaAPI):
    URL = "/api/clientes/"

    def datos_validos(self, **cambios):
        datos = {
            "cedula_juridica": "3-101-777777",
            "nombre": "Importadora Esparza S.A.",
            "correo": "info@esparza.test",
            "telefono": "2635-1234",
        }
        datos.update(cambios)
        return datos

    def test_crear_cliente(self):
        """[CRUD] Crear cliente -> 201."""
        self.como_operador()
        r = self.client.post(self.URL, self.datos_validos())
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Cliente.objects.filter(cedula_juridica="3-101-777777").exists())

    def test_listar_clientes_paginado(self):
        """[CRUD][PAGINACIÓN] Listar -> 200 con count/next/results y tamaño de página."""
        for _ in range(3):
            crear_cliente()
        self.como_consulta()
        r = self.client.get(self.URL, {"tamano": 2})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(len(r.data["results"]), 2)
        self.assertIsNotNone(r.data["next"])

    def test_actualizar_cliente_con_put(self):
        """[CRUD] Actualizar con PUT -> 200."""
        cliente = crear_cliente()
        self.como_operador()
        r = self.client.put(f"{self.URL}{cliente.id}/", self.datos_validos(nombre="Nombre Nuevo S.A."))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        cliente.refresh_from_db()
        self.assertEqual(cliente.nombre, "Nombre Nuevo S.A.")

    def test_eliminar_cliente_sin_cargas(self):
        """[CRUD] Eliminar (Administrador) -> 204."""
        cliente = crear_cliente()
        self.como_admin()
        r = self.client.delete(f"{self.URL}{cliente.id}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Cliente.objects.filter(pk=cliente.id).exists())

    def test_cliente_inexistente_devuelve_404(self):
        """[ERROR] Detalle de un id que no existe -> 404."""
        self.como_consulta()
        r = self.client.get(f"{self.URL}99999/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(r.data["codigo"], "no_encontrado")

    def test_busqueda_por_nombre(self):
        """[BÚSQUEDA] ?buscar= filtra por nombre."""
        crear_cliente(nombre="Frutas del Pacífico")
        crear_cliente(nombre="Repuestos Central")
        self.como_consulta()
        r = self.client.get(self.URL, {"buscar": "frutas"})
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(r.data["results"][0]["nombre"], "Frutas del Pacífico")


class ClienteReglasTests(PruebaAPI):
    URL = "/api/clientes/"

    def test_cedula_con_formato_invalido_devuelve_400(self):
        """[REGLA RN-01] Cédula jurídica con formato incorrecto -> 400."""
        self.como_operador()
        datos = {"cedula_juridica": "3101123", "nombre": "Cliente X", "correo": "x@x.test", "telefono": "2222-3333"}
        r = self.client.post(self.URL, datos)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cedula_juridica", r.data["detalle"])

    def test_cedula_duplicada_devuelve_400(self):
        """[REGLA RN-01] Cédula jurídica repetida -> 400."""
        existente = crear_cliente()
        self.como_operador()
        datos = {"cedula_juridica": existente.cedula_juridica, "nombre": "Otro", "correo": "otro@x.test", "telefono": "2222-3333"}
        r = self.client.post(self.URL, datos)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_se_desactiva_cliente_con_tramites_activos_por_patch(self):
        """[REGLA RN-05] PATCH activo=false con trámites activos -> 400 (invariante protegido en PATCH)."""
        cliente = crear_cliente()
        crear_tramite(carga=crear_carga(cliente=cliente), estado=Tramite.Estado.EN_REVISION)
        self.como_operador()
        r = self.client.patch(f"{self.URL}{cliente.id}/", {"activo": False})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        cliente.refresh_from_db()
        self.assertTrue(cliente.activo)

    def test_eliminar_cliente_con_cargas_devuelve_409(self):
        """[POLÍTICA DE BORRADO] Cliente con cargas (PROTECT) -> 409."""
        cliente = crear_cliente()
        crear_carga(cliente=cliente)
        self.como_admin()
        r = self.client.delete(f"{self.URL}{cliente.id}/")
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)


class ClientePermisosTests(PruebaAPI):
    URL = "/api/clientes/"

    def test_rol_consulta_no_puede_crear(self):
        """[PERMISO] Consulta intenta crear -> 403."""
        self.como_consulta()
        r = self.client.post(self.URL, {"nombre": "X"})
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_operador_no_puede_eliminar(self):
        """[PERMISO] Operador intenta eliminar -> 403."""
        cliente = crear_cliente()
        self.como_operador()
        r = self.client.delete(f"{self.URL}{cliente.id}/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Cliente.objects.filter(pk=cliente.id).exists())
