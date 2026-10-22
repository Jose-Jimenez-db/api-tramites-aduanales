"""
Permisos por rol.

Roles del sistema (grupos de Django creados por la migración cuentas/0001):
    - Administrador: todo, incluido eliminar y administrar usuarios.
    - Operador: consultar, crear y modificar; no puede eliminar.
    - Consulta: solo lectura.

Matriz por defecto (cada vista puede cambiarla):

    Método            Administrador  Operador  Consulta
    GET/HEAD/OPTIONS        sí          sí        sí
    POST/PUT/PATCH          sí          sí        no
    DELETE                  sí          no        no
"""
from rest_framework.permissions import BasePermission

ADMINISTRADOR = "Administrador"
OPERADOR = "Operador"
CONSULTA = "Consulta"
ROLES = (ADMINISTRADOR, OPERADOR, CONSULTA)

TODOS = {ADMINISTRADOR, OPERADOR, CONSULTA}
ESCRITURA = {ADMINISTRADOR, OPERADOR}
SOLO_ADMIN = {ADMINISTRADOR}

MATRIZ_POR_DEFECTO = {
    "GET": TODOS,
    "HEAD": TODOS,
    "OPTIONS": TODOS,
    "POST": ESCRITURA,
    "PUT": ESCRITURA,
    "PATCH": ESCRITURA,
    "DELETE": SOLO_ADMIN,
}


def obtener_rol(usuario):
    """Devuelve el rol del usuario o None si no tiene ninguno."""
    if not usuario or not usuario.is_authenticated:
        return None
    if usuario.is_superuser:
        return ADMINISTRADOR
    # Se guarda en el objeto para no consultar la base de datos varias veces.
    if not hasattr(usuario, "_rol_cache"):
        grupos = set(usuario.groups.values_list("name", flat=True))
        usuario._rol_cache = next((rol for rol in ROLES if rol in grupos), None)
    return usuario._rol_cache


class PermisoPorRol(BasePermission):
    """
    Revisa el rol del usuario contra la matriz de permisos.

    Una vista puede definir:
      - roles_por_metodo = {"GET": {...}, ...}   -> reemplaza la matriz por defecto
      - roles_por_accion = {"anular": {...}}      -> reglas para acciones específicas
    """

    message = "Su rol no tiene permiso para realizar esta operación."

    def has_permission(self, request, view):
        # Sin autenticación: DRF responde 401 automáticamente.
        if not request.user or not request.user.is_authenticated:
            return False

        rol = obtener_rol(request.user)
        if rol is None:
            return False

        accion = getattr(view, "action", None)
        roles_por_accion = getattr(view, "roles_por_accion", {})
        if accion in roles_por_accion:
            return rol in roles_por_accion[accion]

        matriz = getattr(view, "roles_por_metodo", None) or MATRIZ_POR_DEFECTO
        return rol in matriz.get(request.method, set())
