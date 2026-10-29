from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response

from .permisos import SOLO_ADMIN, TODOS, obtener_rol, validar_rol
from .serializers import LoginSerializer, UsuarioSerializer

Usuario = get_user_model()


@api_view(['POST'])
@authentication_classes([])  # el login no necesita token
def login_api(request):
    """POST /api/auth/login/   {"username": "...", "password": "..."} -> token y rol"""
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


@api_view(['POST'])
def logout_api(request):
    """POST /api/auth/logout/ -> elimina el token actual"""
    error = validar_rol(request, TODOS)
    if error:
        return error
    Token.objects.filter(user=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def perfil_api(request):
    """GET /api/auth/perfil/ -> datos del usuario autenticado"""
    error = validar_rol(request, TODOS)
    if error:
        return error
    return Response(UsuarioSerializer(request.user).data)


@api_view(['GET', 'POST'])
def usuarios_api(request):
    """Administración de usuarios: solo el rol Administrador."""
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
