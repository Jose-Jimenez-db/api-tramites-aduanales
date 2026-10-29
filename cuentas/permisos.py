"""
Roles del sistema y revisión de permisos.

Los roles son grupos de Django (Group). Se crean con get_or_create la primera vez
que se asignan a un usuario:
    - Administrador: todo, incluido eliminar y administrar usuarios.
    - Operador: consultar, crear y modificar; no puede eliminar.
    - Consulta: solo lectura.

Matriz de permisos:

    Método            Administrador  Operador  Consulta
    GET                     sí          sí        sí
    POST/PUT/PATCH          sí          sí        no
    DELETE                  sí          no        no
"""
from rest_framework import status
from rest_framework.response import Response

ADMINISTRADOR = "Administrador"
OPERADOR = "Operador"
CONSULTA = "Consulta"
ROLES = [ADMINISTRADOR, OPERADOR, CONSULTA]

TODOS = [ADMINISTRADOR, OPERADOR, CONSULTA]
ESCRITURA = [ADMINISTRADOR, OPERADOR]
SOLO_ADMIN = [ADMINISTRADOR]

# Roles permitidos según el método HTTP
ROLES_POR_METODO = {
    "GET": TODOS,
    "POST": ESCRITURA,
    "PUT": ESCRITURA,
    "PATCH": ESCRITURA,
    "DELETE": SOLO_ADMIN,
}


# Qué hace: Se obtiene el rol del usuario, o sea el nombre de su grupo (Administrador, Operador o
#     Consulta).
# Qué usa: El usuario que viene en la solicitud, el campo is_superuser y la tabla de grupos de
#     Django (Group).
# Cómo lo hace: Si el usuario es superusuario se toma como Administrador. Si no, se busca el primer
#     grupo del usuario que esté en la lista ROLES y se devuelve su nombre. Si no tiene ninguno se
#     devuelve None.
def obtener_rol(usuario):
    if usuario.is_superuser:
        return ADMINISTRADOR
    grupo = usuario.groups.filter(name__in=ROLES).first()
    return grupo.name if grupo else None


# Qué hace: Se revisa si el usuario puede hacer la operación que está pidiendo. Se llama al inicio
#     de todas las vistas.
# Qué usa: request.user, la función obtener_rol, el diccionario ROLES_POR_METODO y Response con los
#     códigos 401 y 403.
# Cómo lo hace: Primero se revisa si el usuario inició sesión; si no, se responde 401. Si no se
#     mandan roles permitidos, se toman de la matriz según el método HTTP (GET, POST, DELETE...).
#     Después se compara el rol del usuario con esa lista; si no está, se responde 403. Si todo
#     está bien se devuelve None y la vista sigue normal.
def validar_rol(request, roles_permitidos=None):
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Autenticación requerida."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    if roles_permitidos is None:
        roles_permitidos = ROLES_POR_METODO.get(request.method, [])
    if obtener_rol(request.user) not in roles_permitidos:
        return Response(
            {"detail": "Su rol no tiene permiso para realizar esta operación."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None
