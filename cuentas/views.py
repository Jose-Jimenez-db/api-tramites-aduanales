from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permisos import SOLO_ADMIN, obtener_rol

from .serializers import LoginSerializer, UsuarioSerializer

Usuario = get_user_model()


class LoginView(APIView):
    """POST /api/auth/login/ -> devuelve el token del usuario."""

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = LoginSerializer

    @extend_schema(request=LoginSerializer, responses={200: dict})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.validated_data["usuario"]
        token, _ = Token.objects.get_or_create(user=usuario)
        return Response(
            {
                "token": token.key,
                "usuario": usuario.username,
                "rol": obtener_rol(usuario),
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """POST /api/auth/logout/ -> elimina el token actual."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PerfilView(APIView):
    """GET /api/auth/perfil/ -> datos del usuario autenticado."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UsuarioSerializer)
    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)


class UsuarioViewSet(viewsets.ModelViewSet):
    """Administración de usuarios: solo el rol Administrador."""

    queryset = Usuario.objects.prefetch_related("groups").order_by("username")
    serializer_class = UsuarioSerializer
    roles_por_metodo = {metodo: SOLO_ADMIN for metodo in ("GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE")}
    search_fields = ["username", "first_name", "last_name", "email"]
    ordering_fields = ["username", "date_joined"]
    filterset_fields = ["is_active"]
