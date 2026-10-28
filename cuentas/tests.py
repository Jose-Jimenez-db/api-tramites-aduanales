import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.authtoken.models import Token

from cuentas.pruebas import PruebaAPI

Usuario = get_user_model()


class AutenticacionTests(PruebaAPI):
    URL_LOGIN = "/api/auth/login/"

    def setUp(self):
        # Contraseña generada en tiempo de ejecución: no se guarda en el repositorio
        self.clave = secrets.token_urlsafe(16)
        self.usuario = Usuario.objects.create_user(username="login_prueba", password=self.clave)
        grupo, _ = Group.objects.get_or_create(name="Operador")
        self.usuario.groups.add(grupo)

    def test_login_correcto_devuelve_token_y_rol(self):
        """[SEGURIDAD] Login correcto -> 200 con token y rol."""
        r = self.client.post(self.URL_LOGIN, {"username": "login_prueba", "password": self.clave})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["rol"], "Operador")
        self.assertTrue(Token.objects.filter(user=self.usuario, key=r.data["token"]).exists())

    def test_login_con_clave_incorrecta_devuelve_400(self):
        """[SEGURIDAD] Credenciales incorrectas -> 400 sin token."""
        r = self.client.post(self.URL_LOGIN, {"username": "login_prueba", "password": "otra-clave"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("token", r.data)

    def test_peticion_sin_token_devuelve_401(self):
        """[PERMISO] Sin token -> 401."""
        r = self.client.get("/api/clientes/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", r.data)

    def test_token_invalido_devuelve_401(self):
        """[PERMISO] Token inventado -> 401."""
        self.client.credentials(HTTP_AUTHORIZATION="Token token-que-no-existe")
        r = self.client.get("/api/clientes/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_elimina_el_token(self):
        """[SEGURIDAD] Logout -> 204 y el token deja de servir."""
        self.como_operador()
        r = self.client.post("/api/auth/logout/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.client.get("/api/clientes/").status_code, status.HTTP_401_UNAUTHORIZED)


class UsuariosTests(PruebaAPI):
    URL = "/api/auth/usuarios/"

    def test_operador_no_puede_listar_usuarios(self):
        """[PERMISO] Solo el Administrador administra usuarios -> 403."""
        self.como_operador()
        self.assertEqual(self.client.get(self.URL).status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_crea_usuario_con_rol(self):
        """[CRUD] El Administrador crea un usuario con rol -> 201."""
        self.como_admin()
        datos = {"username": "nuevo_operador", "rol": "Operador", "password": "Una-Clave-Larga-2026"}
        r = self.client.post(self.URL, datos)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["rol"], "Operador")
        self.assertNotIn("password", r.data)
        self.assertTrue(Usuario.objects.get(username="nuevo_operador").groups.filter(name="Operador").exists())
