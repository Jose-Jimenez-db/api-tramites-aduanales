import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.authtoken.models import Token

from cuentas.pruebas import PruebaAPI

Usuario = get_user_model()


# Qué hace: Se agrupan las pruebas del login, el logout y los errores 401.
# Qué usa: PruebaAPI como clase base.
# Cómo lo hace: Cada método que empieza con test_ es una prueba que Django corre con python
#     manage.py test.
class AutenticacionTests(PruebaAPI):
    URL_LOGIN = "/api/auth/login/"

    # Qué hace: Se prepara un usuario con contraseña para probar el login. Se corre antes de cada
    #     prueba.
    # Qué usa: secrets.token_urlsafe, create_user y Group.objects.get_or_create.
    # Cómo lo hace: La contraseña se genera al azar en el momento, así no queda escrita en el
    #     repositorio. Se crea el usuario login_prueba con esa contraseña y el rol Operador.
    def setUp(self):
        # Contraseña generada en tiempo de ejecución: no se guarda en el repositorio
        self.clave = secrets.token_urlsafe(16)
        self.usuario = Usuario.objects.create_user(username="login_prueba", password=self.clave)
        grupo, _ = Group.objects.get_or_create(name="Operador")
        self.usuario.groups.add(grupo)

    # Qué hace: Se prueba que con datos correctos el login responda 200 con el token y el rol.
    # Qué usa: self.client.post y el modelo Token.
    # Cómo lo hace: Se manda el usuario y la contraseña al login, se revisa el código 200, que el
    #     rol sea Operador y que el token que devolvió exista en la base de datos.
    def test_login_correcto_devuelve_token_y_rol(self):
        """[SEGURIDAD] Login correcto -> 200 con token y rol."""
        r = self.client.post(self.URL_LOGIN, {"username": "login_prueba", "password": self.clave})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["rol"], "Operador")
        self.assertTrue(Token.objects.filter(user=self.usuario, key=r.data["token"]).exists())

    # Qué hace: Se prueba que con una contraseña incorrecta el login responda 400 y no dé token.
    # Qué usa: self.client.post.
    # Cómo lo hace: Se manda una contraseña equivocada y se revisa que la respuesta sea 400 y no
    #     traiga la llave token.
    def test_login_con_clave_incorrecta_devuelve_400(self):
        """[SEGURIDAD] Credenciales incorrectas -> 400 sin token."""
        r = self.client.post(self.URL_LOGIN, {"username": "login_prueba", "password": "otra-clave"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("token", r.data)

    # Qué hace: Se prueba que sin token la API responda 401.
    # Qué usa: self.client.get.
    # Cómo lo hace: Se pide la lista de clientes sin iniciar sesión y se revisa el código 401 y el
    #     mensaje en detail.
    def test_peticion_sin_token_devuelve_401(self):
        """[PERMISO] Sin token -> 401."""
        r = self.client.get("/api/clientes/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", r.data)

    # Qué hace: Se prueba que con un token inventado la API responda 401.
    # Qué usa: self.client.credentials y self.client.get.
    # Cómo lo hace: Se pone un token que no existe en el encabezado y se revisa que la respuesta
    #     sea 401.
    def test_token_invalido_devuelve_401(self):
        """[PERMISO] Token inventado -> 401."""
        self.client.credentials(HTTP_AUTHORIZATION="Token token-que-no-existe")
        r = self.client.get("/api/clientes/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    # Qué hace: Se prueba que después del logout el token ya no sirva.
    # Qué usa: como_operador y self.client.post / get.
    # Cómo lo hace: Se inicia sesión, se hace logout (204) y luego se intenta usar el mismo token;
    #     debe dar 401.
    def test_logout_elimina_el_token(self):
        """[SEGURIDAD] Logout -> 204 y el token deja de servir."""
        self.como_operador()
        r = self.client.post("/api/auth/logout/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.client.get("/api/clientes/").status_code, status.HTTP_401_UNAUTHORIZED)


# Qué hace: Se agrupan las pruebas de la administración de usuarios.
# Qué usa: PruebaAPI como clase base.
# Cómo lo hace: Cada método test_ revisa un caso de /api/auth/usuarios/.
class UsuariosTests(PruebaAPI):
    URL = "/api/auth/usuarios/"

    # Qué hace: Se prueba que el Operador no pueda ver los usuarios (403).
    # Qué usa: como_operador y self.client.get.
    # Cómo lo hace: Se inicia sesión como Operador, se pide la lista de usuarios y se revisa que dé
    #     403.
    def test_operador_no_puede_listar_usuarios(self):
        """[PERMISO] Solo el Administrador administra usuarios -> 403."""
        self.como_operador()
        self.assertEqual(self.client.get(self.URL).status_code, status.HTTP_403_FORBIDDEN)

    # Qué hace: Se prueba que el Administrador pueda crear un usuario con rol.
    # Qué usa: como_admin, self.client.post y el modelo de usuario.
    # Cómo lo hace: Se crea un usuario con rol Operador, se revisa el 201, que el rol venga en la
    #     respuesta, que la contraseña NO venga, y que el usuario quedó en el grupo Operador.
    def test_admin_crea_usuario_con_rol(self):
        """[CRUD] El Administrador crea un usuario con rol -> 201."""
        self.como_admin()
        datos = {"username": "nuevo_operador", "rol": "Operador", "password": "Una-Clave-Larga-2026"}
        r = self.client.post(self.URL, datos)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["rol"], "Operador")
        self.assertNotIn("password", r.data)
        self.assertTrue(Usuario.objects.get(username="nuevo_operador").groups.filter(name="Operador").exists())
