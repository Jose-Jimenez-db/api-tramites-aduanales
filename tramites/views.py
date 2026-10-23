from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.excepciones import Conflicto
from core.permisos import SOLO_ADMIN, TODOS

from . import servicios
from .filters import TramiteFilter
from .models import PermisoTramite, TipoPermiso, Tramite
from .serializers import (
    CambiarEstadoSerializer,
    PermisoTramiteSerializer,
    ResolverPermisoSerializer,
    TipoPermisoSerializer,
    TramiteSerializer,
)


class TipoPermisoViewSet(viewsets.ModelViewSet):
    """Catálogo de permisos. Solo el Administrador lo modifica."""

    queryset = TipoPermiso.objects.all()
    serializer_class = TipoPermisoSerializer
    roles_por_metodo = {
        "GET": TODOS, "HEAD": TODOS, "OPTIONS": TODOS,
        "POST": SOLO_ADMIN, "PUT": SOLO_ADMIN, "PATCH": SOLO_ADMIN, "DELETE": SOLO_ADMIN,
    }
    filterset_fields = ["aplica_a", "activo"]
    search_fields = ["codigo", "nombre", "institucion"]
    ordering_fields = ["codigo", "nombre"]


class TramiteViewSet(viewsets.ModelViewSet):
    """
    CRUD de trámites + acciones del proceso:
      POST /api/tramites/{id}/cambiar-estado/
      POST /api/tramites/{id}/resolver-permiso/
    """

    # select_related: carga, cliente y transportista en la misma consulta (JOIN)
    # prefetch_related: permisos y cobros en una consulta adicional cada uno
    queryset = Tramite.objects.select_related(
        "carga__cliente", "transportista", "creado_por"
    ).prefetch_related(
        Prefetch("permisos_tramite", queryset=PermisoTramite.objects.select_related("tipo_permiso")),
        "cobros",
    )
    serializer_class = TramiteSerializer
    filterset_class = TramiteFilter
    search_fields = ["codigo", "carga__numero_contenedor", "carga__cliente__nombre", "observaciones"]
    ordering_fields = ["fecha_creacion", "codigo", "estado", "fecha_liberacion"]
    ordering = ["-fecha_creacion"]

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)

    def update(self, request, *args, **kwargs):
        # RN-12: un trámite cerrado no se modifica (aplica a PUT y PATCH)
        tramite = self.get_object()
        if tramite.estado in Tramite.ESTADOS_CERRADOS:
            raise Conflicto("El trámite está liberado o cancelado y no se puede modificar.")
        return super().update(request, *args, **kwargs)

    def perform_destroy(self, instance):
        # RN-12: solo se eliminan trámites recién registrados; los demás se cancelan
        if instance.estado != Tramite.Estado.REGISTRADO:
            raise Conflicto("Solo se pueden eliminar trámites en estado REGISTRADO. Use la cancelación.")
        instance.delete()

    def _respuesta(self, tramite):
        tramite = self.get_queryset().get(pk=tramite.pk)
        return Response(TramiteSerializer(tramite, context=self.get_serializer_context()).data)

    @extend_schema(request=CambiarEstadoSerializer, responses=TramiteSerializer)
    @action(detail=True, methods=["post"], url_path="cambiar-estado")
    def cambiar_estado(self, request, pk=None):
        tramite = self.get_object()
        entrada = CambiarEstadoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        servicios.cambiar_estado(tramite, entrada.validated_data["estado"])
        return self._respuesta(tramite)

    @extend_schema(request=ResolverPermisoSerializer, responses=PermisoTramiteSerializer)
    @action(detail=True, methods=["post"], url_path="resolver-permiso")
    def resolver_permiso(self, request, pk=None):
        tramite = self.get_object()
        entrada = ResolverPermisoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        permiso = servicios.resolver_permiso(tramite, **entrada.validated_data)
        return Response(PermisoTramiteSerializer(permiso).data)
