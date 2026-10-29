from rest_framework import status

from cuentas.pruebas import PruebaAPI, crear_carga, crear_cliente, crear_tramite
from tramites.models import Tramite

from .models import Cliente


# Qué hace: Se agrupan las pruebas del CRUD de clientes, la paginación y la búsqueda.
# Qué usa: PruebaAPI como clase base.
# Cómo lo hace: URL es la ruta que usan todas las pruebas de esta clase.
class ClienteCRUDTests(PruebaAPI):
    URL = "/api/clientes/"

    # Qué hace: Se devuelven datos válidos para crear un cliente; la prueba puede cambiar alguno.
    # Qué usa: Un diccionario y update().
    # Cómo lo hace: Se arma un diccionario con datos correctos y se le aplican los cambios que
    #     mande la prueba.
    def datos_validos(self, **cambios):
        datos = {
            "cedula_juridica": "3-101-777777",
            "nombre": "Importadora Esparza S.A.",
            "correo": "info@esparza.test",
            "telefono": "2635-1234",
        }
        datos.update(cambios)
        return datos

    # Qué hace: Se prueba que el Operador pueda crear un cliente (201).
    # Qué usa: como_operador, self.client.post y el modelo Cliente.
    # Cómo lo hace: Se manda el POST con datos válidos, se revisa el 201 y que el cliente quedó en
    #     la base de datos.
    def test_crear_cliente(self):
        """[CRUD] Crear cliente -> 201."""
        self.como_operador()
        r = self.client.post(self.URL, self.datos_validos())
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Cliente.objects.filter(cedula_juridica="3-101-777777").exists())

    # Qué hace: Se prueba que la lista venga de 5 en 5.
    # Qué usa: crear_cliente, como_consulta y self.client.get.
    # Cómo lo hace: Se crean 6 clientes y se pide la página 1: deben venir 5 resultados, 6 en total
    #     y 2 páginas.
    def test_listar_clientes_paginado(self):
        """[CRUD][PAGINACIÓN] Listar -> 200 con 5 resultados por página."""
        for _ in range(6):
            crear_cliente()
        self.como_consulta()
        r = self.client.get(self.URL, {"page": 1})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["total_registros"], 6)
        self.assertEqual(len(r.data["resultados"]), 5)
        self.assertEqual(r.data["total_paginas"], 2)

    # Qué hace: Se prueba que un cliente se pueda editar con PUT (200).
    # Qué usa: crear_cliente, como_operador, self.client.put y refresh_from_db.
    # Cómo lo hace: Se cambia el nombre con PUT y se vuelve a leer el cliente de la base de datos
    #     para revisar que el nombre sí cambió.
    def test_actualizar_cliente_con_put(self):
        """[CRUD] Actualizar con PUT -> 200."""
        cliente = crear_cliente()
        self.como_operador()
        r = self.client.put(f"{self.URL}{cliente.id}/", self.datos_validos(nombre="Nombre Nuevo S.A."))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        cliente.refresh_from_db()
        self.assertEqual(cliente.nombre, "Nombre Nuevo S.A.")

    # Qué hace: Se prueba que el Administrador pueda borrar un cliente sin cargas (204).
    # Qué usa: crear_cliente, como_admin y self.client.delete.
    # Cómo lo hace: Se borra el cliente y se revisa el 204 y que ya no exista en la base de datos.
    def test_eliminar_cliente_sin_cargas(self):
        """[CRUD] Eliminar (Administrador) -> 204."""
        cliente = crear_cliente()
        self.como_admin()
        r = self.client.delete(f"{self.URL}{cliente.id}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Cliente.objects.filter(pk=cliente.id).exists())

    # Qué hace: Se prueba que pedir un cliente que no existe responda 404.
    # Qué usa: como_consulta y self.client.get.
    # Cómo lo hace: Se pide el id 99999 y se revisa el 404 y que la respuesta traiga la llave
    #     error.
    def test_cliente_inexistente_devuelve_404(self):
        """[ERROR] Detalle de un id que no existe -> 404."""
        self.como_consulta()
        r = self.client.get(f"{self.URL}99999/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", r.data)

    # Qué hace: Se prueba la búsqueda con ?buscar=.
    # Qué usa: crear_cliente, como_consulta y self.client.get.
    # Cómo lo hace: Se crean dos clientes con nombres distintos, se busca "frutas" y debe salir
    #     solo uno.
    def test_busqueda_por_nombre(self):
        """[BÚSQUEDA] ?buscar= filtra por nombre."""
        crear_cliente(nombre="Frutas del Pacífico")
        crear_cliente(nombre="Repuestos Central")
        self.como_consulta()
        r = self.client.get(self.URL, {"buscar": "frutas"})
        self.assertEqual(r.data["total_registros"], 1)
        self.assertEqual(r.data["resultados"][0]["nombre"], "Frutas del Pacífico")


    # Qué hace: Se prueba que un filtro con un valor raro responda 400.
    # Qué usa: como_consulta y self.client.get.
    # Cómo lo hace: Se manda ?activo=quizas (que no es true ni false) y se revisa el 400 con el
    #     campo activo.
    def test_filtro_con_valor_invalido_devuelve_400(self):
        """[FILTRO][VALIDACIÓN] ?activo=quizas no es true/false -> 400."""
        self.como_consulta()
        r = self.client.get(self.URL, {"activo": "quizas"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("activo", r.data)


# Qué hace: Se agrupan las pruebas de las reglas de negocio de clientes.
# Qué usa: PruebaAPI como clase base.
# Cómo lo hace: Cada método test_ revisa una regla (RN-01, RN-05) o la política de borrado.
class ClienteReglasTests(PruebaAPI):
    URL = "/api/clientes/"

    # Qué hace: RN-01: se prueba que una cédula mal escrita responda 400.
    # Qué usa: como_operador y self.client.post.
    # Cómo lo hace: Se manda la cédula 3101123 (sin guiones) y se revisa el 400 con el campo
    #     cedula_juridica.
    def test_cedula_con_formato_invalido_devuelve_400(self):
        """[REGLA RN-01] Cédula jurídica con formato incorrecto -> 400."""
        self.como_operador()
        datos = {"cedula_juridica": "3101123", "nombre": "Cliente X", "correo": "x@x.test", "telefono": "2222-3333"}
        r = self.client.post(self.URL, datos)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cedula_juridica", r.data)

    # Qué hace: RN-01: se prueba que no se pueda repetir una cédula jurídica.
    # Qué usa: crear_cliente, como_operador y self.client.post.
    # Cómo lo hace: Se crea un cliente y se intenta crear otro con la misma cédula; debe dar 400.
    def test_cedula_duplicada_devuelve_400(self):
        """[REGLA RN-01] Cédula jurídica repetida -> 400."""
        existente = crear_cliente()
        self.como_operador()
        datos = {"cedula_juridica": existente.cedula_juridica, "nombre": "Otro", "correo": "otro@x.test", "telefono": "2222-3333"}
        r = self.client.post(self.URL, datos)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    # Qué hace: RN-05: se prueba que no se pueda desactivar con PATCH un cliente con trámites
    #     activos.
    # Qué usa: crear_cliente, crear_carga, crear_tramite, self.client.patch y refresh_from_db.
    # Cómo lo hace: Se crea un cliente con un trámite EN_REVISION, se manda PATCH activo=false y se
    #     revisa el 400 y que el cliente siga activo en la base de datos.
    def test_no_se_desactiva_cliente_con_tramites_activos_por_patch(self):
        """[REGLA RN-05] PATCH activo=false con trámites activos -> 400 (invariante protegido en PATCH)."""
        cliente = crear_cliente()
        crear_tramite(carga=crear_carga(cliente=cliente), estado=Tramite.Estado.EN_REVISION)
        self.como_operador()
        r = self.client.patch(f"{self.URL}{cliente.id}/", {"activo": False})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        cliente.refresh_from_db()
        self.assertTrue(cliente.activo)

    # Qué hace: Se prueba que no se pueda borrar un cliente que tiene cargas (409).
    # Qué usa: crear_cliente, crear_carga, como_admin y self.client.delete.
    # Cómo lo hace: Se crea un cliente con una carga y se intenta borrar como Administrador; por el
    #     PROTECT debe dar 409.
    def test_eliminar_cliente_con_cargas_devuelve_409(self):
        """[POLÍTICA DE BORRADO] Cliente con cargas (PROTECT) -> 409."""
        cliente = crear_cliente()
        crear_carga(cliente=cliente)
        self.como_admin()
        r = self.client.delete(f"{self.URL}{cliente.id}/")
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)


# Qué hace: Se agrupan las pruebas de permisos por rol en clientes.
# Qué usa: PruebaAPI como clase base.
# Cómo lo hace: Cada método test_ revisa que un rol sin permiso reciba 403.
class ClientePermisosTests(PruebaAPI):
    URL = "/api/clientes/"

    # Qué hace: Se prueba que el rol Consulta no pueda crear clientes (403).
    # Qué usa: como_consulta y self.client.post.
    # Cómo lo hace: Se intenta un POST como Consulta y se revisa el 403.
    def test_rol_consulta_no_puede_crear(self):
        """[PERMISO] Consulta intenta crear -> 403."""
        self.como_consulta()
        r = self.client.post(self.URL, {"nombre": "X"})
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    # Qué hace: Se prueba que el Operador no pueda borrar clientes (403).
    # Qué usa: crear_cliente, como_operador y self.client.delete.
    # Cómo lo hace: Se intenta borrar como Operador, se revisa el 403 y que el cliente siga
    #     existiendo.
    def test_operador_no_puede_eliminar(self):
        """[PERMISO] Operador intenta eliminar -> 403."""
        cliente = crear_cliente()
        self.como_operador()
        r = self.client.delete(f"{self.URL}{cliente.id}/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Cliente.objects.filter(pk=cliente.id).exists())
