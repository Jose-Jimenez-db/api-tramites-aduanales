from rest_framework import status

from cuentas.pruebas import PruebaAPI, crear_transportista


# Qué hace: Se agrupan las pruebas de transportistas.
# Qué usa: PruebaAPI como clase base.
# Cómo lo hace: Cada método test_ revisa un caso de /api/transportistas/.
class TransportistaTests(PruebaAPI):
    URL = "/api/transportistas/"

    # Qué hace: Se prueba crear un transportista y que venga licencia_vigente calculada.
    # Qué usa: como_operador y self.client.post.
    # Cómo lo hace: Se crea uno con licencia que vence en 2030; debe dar 201 y licencia_vigente en
    #     True.
    def test_crear_transportista(self):
        """[CRUD] Crear transportista -> 201 con licencia_vigente calculada."""
        self.como_operador()
        datos = {
            "cedula": "6-0123-0456",
            "nombre": "Carlos Mora Vega",
            "telefono": "8777-1234",
            "numero_licencia": "LIC-9001",
            "vencimiento_licencia": "2030-01-31",
            "placa_cabezal": "C-123456",
        }
        r = self.client.post(self.URL, datos)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertTrue(r.data["licencia_vigente"])

    # Qué hace: Se prueba que una placa mal escrita responda 400.
    # Qué usa: como_operador y self.client.post.
    # Cómo lo hace: Se manda la placa ABC123 y se revisa el 400 con el campo placa_cabezal.
    def test_placa_con_formato_invalido_devuelve_400(self):
        """[VALIDACIÓN] Placa de cabezal con formato incorrecto -> 400."""
        self.como_operador()
        datos = {
            "cedula": "6-0123-0457", "nombre": "Ana Ruiz", "telefono": "8777-1235",
            "numero_licencia": "LIC-9002", "vencimiento_licencia": "2030-01-31", "placa_cabezal": "ABC123",
        }
        r = self.client.post(self.URL, datos)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("placa_cabezal", r.data)

    # Qué hace: Se prueba que los filtros ?licencia_vigente= y ?activo= funcionen juntos.
    # Qué usa: crear_transportista, como_consulta y self.client.get.
    # Cómo lo hace: Se crean 3: uno vigente y activo, uno vencido y uno inactivo. Con los dos
    #     filtros en true debe salir solo 1.
    def test_filtro_combinado_licencia_vigente_y_activo(self):
        """[FILTRO] ?licencia_vigente=true&activo=true combina dos filtros."""
        crear_transportista(dias_licencia=100)
        crear_transportista(dias_licencia=-5)
        crear_transportista(dias_licencia=100, activo=False)
        self.como_consulta()
        r = self.client.get(self.URL, {"licencia_vigente": "true", "activo": "true"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["total_registros"], 1)
