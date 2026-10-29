from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response

from .permisos import SOLO_ADMIN, TODOS, obtener_rol, validar_rol
from .serializers import LoginSerializer, UsuarioSerializer

Usuario = get_user_model()


# Qué hace: POST /api/auth/login/ . Se inicia sesión: se recibe usuario y contraseña y se devuelve
#     el token y el rol.
# Qué usa: @api_view, @authentication_classes([]), LoginSerializer, Token de
#     rest_framework.authtoken y obtener_rol.
# Cómo lo hace: Se quita la autenticación de esta vista porque para iniciar sesión todavía no hay
#     token. Se validan los datos con LoginSerializer (si están mal, 400). Luego se busca o se crea
#     el token del usuario con Token.objects.get_or_create y se responde con el token, el usuario y
#     el rol.
@api_view(['POST'])
@authentication_classes([])  # el login no necesita token
def login_api(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    usuario = serializer.validated_data['usuario']
    token, _ = Token.objects.get_or_create(user=usuario)
    return Response({
        'token': token.key,
        'usuario': usuario.username,
        'rol': obtener_rol(usuario)
    })


# Qué hace: POST /api/auth/logout/ . Se cierra la sesión borrando el token del usuario.
# Qué usa: @api_view, validar_rol y el modelo Token.
# Cómo lo hace: Se revisa que el usuario tenga sesión con validar_rol. Después se borra su token de
#     la base de datos, así el token ya no sirve más. Se responde 204 sin contenido.
@api_view(['POST'])
def logout_api(request):
    error = validar_rol(request, TODOS)
    if error:
        return error
    Token.objects.filter(user=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# Qué hace: GET /api/auth/perfil/ . Se devuelven los datos del usuario que tiene la sesión
#     iniciada.
# Qué usa: @api_view, validar_rol y UsuarioSerializer.
# Cómo lo hace: Se revisa que el usuario tenga sesión (cualquier rol sirve) y se responde con sus
#     datos convertidos a JSON, incluido el rol.
@api_view(['GET'])
def perfil_api(request):
    error = validar_rol(request, TODOS)
    if error:
        return error
    return Response(UsuarioSerializer(request.user).data)


# Qué hace: GET y POST /api/auth/usuarios/ . Se listan todos los usuarios o se crea uno nuevo. Solo
#     lo puede hacer el Administrador.
# Qué usa: @api_view, validar_rol con SOLO_ADMIN, el modelo de usuario y UsuarioSerializer.
# Cómo lo hace: Primero se revisa que sea Administrador (si no, 403). Si es GET se traen los
#     usuarios ordenados por username. Si es POST se validan los datos con el serializador; si
#     están bien se guarda y se responde 201, si no se responde 400 con los errores.
@api_view(['GET', 'POST'])
def usuarios_api(request):
    error = validar_rol(request, SOLO_ADMIN)
    if error:
        return error

    if request.method == 'GET':
        usuarios = Usuario.objects.order_by('username')
        return Response(UsuarioSerializer(usuarios, many=True).data)

    serializer = UsuarioSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Qué hace: GET, PUT, PATCH y DELETE /api/auth/usuarios/<id>/ . Se ve, se edita o se borra un
#     usuario. Solo lo puede hacer el Administrador.
# Qué usa: @api_view, validar_rol con SOLO_ADMIN, el modelo de usuario y UsuarioSerializer.
# Cómo lo hace: Se revisa que sea Administrador y se busca el usuario por id (si no existe, 404).
#     GET devuelve sus datos. PUT y PATCH lo editan con el serializador (PATCH con partial=True
#     para mandar solo algunos campos). DELETE lo borra y responde 204.
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def usuario_detalle_api(request, id):
    error = validar_rol(request, SOLO_ADMIN)
    if error:
        return error

    try:
        usuario = Usuario.objects.get(id=id)
    except Usuario.DoesNotExist:
        return Response({'error': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(UsuarioSerializer(usuario).data)

    if request.method in ['PUT', 'PATCH']:
        serializer = UsuarioSerializer(usuario, data=request.data, partial=request.method == 'PATCH')
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    usuario.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
