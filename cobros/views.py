from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.excepciones import Conflicto
from core.permisos import SOLO_ADMIN

from .filters import CobroFilter
from .models import Cobro
from .serializers import CobroSerializer, RegistrarPagoSerializer


class CobroViewSet(viewsets.ModelViewSet):
    """
    CRUD de cobros + acciones:
      POST /api/cobros/{id}/registrar-pago/   (Administrador, Operador)
      POST /api/cobros/{id}/anular/           (solo Administrador)
    """

    queryset = Cobro.objects.select_related("tramite__carga__cliente", "registrado_por")
    serializer_class = CobroSerializer
    filterset_class = CobroFilter
    search_fields = ["numero_factura", "tramite__codigo"]
    ordering_fields = ["fecha_emision", "monto", "fecha_pago"]
    ordering = ["-fecha_emision"]
    roles_por_accion = {"anular": SOLO_ADMIN}

    def perform_create(self, serializer):
        serializer.save(registrado_por=self.request.user)

    def _exigir_pendiente(self, cobro, mensaje):
        # RN-14: un cobro pagado o anulado queda cerrado
        if cobro.estado != Cobro.Estado.PENDIENTE:
            raise Conflicto(mensaje)

    def update(self, request, *args, **kwargs):
        self._exigir_pendiente(self.get_object(), "Un cobro pagado o anulado no se puede modificar.")
        return super().update(request, *args, **kwargs)

    def perform_destroy(self, instance):
        self._exigir_pendiente(instance, "Solo se pueden eliminar cobros pendientes.")
        instance.delete()

    @extend_schema(request=RegistrarPagoSerializer, responses=CobroSerializer)
    @action(detail=True, methods=["post"], url_path="registrar-pago")
    def registrar_pago(self, request, pk=None):
        cobro = self.get_object()
        self._exigir_pendiente(cobro, "El cobro ya fue pagado o anulado.")
        entrada = RegistrarPagoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        cobro.estado = Cobro.Estado.PAGADO
        cobro.metodo_pago = entrada.validated_data["metodo_pago"]
        cobro.fecha_pago = timezone.now()  # decisión automática
        cobro.save(update_fields=["estado", "metodo_pago", "fecha_pago"])
        return Response(CobroSerializer(cobro).data)

    @extend_schema(request=None, responses=CobroSerializer)
    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        cobro = self.get_object()
        self._exigir_pendiente(cobro, "Solo se pueden anular cobros pendientes.")
        cobro.estado = Cobro.Estado.ANULADO
        cobro.save(update_fields=["estado"])
        return Response(CobroSerializer(cobro).data)
