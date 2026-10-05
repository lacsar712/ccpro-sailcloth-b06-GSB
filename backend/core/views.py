from django.db import IntegrityError, transaction
from django.db.models import Count
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ClothRoll, DipRun, Loft, ResinBand
from .serializers import (
    ClothRollSerializer,
    DipRunSerializer,
    LoftSerializer,
    ResinBandSerializer,
)


class IsAdminRole(IsAuthenticated):
    """仅管理员可写；读取仍走普通登录校验。"""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.user.is_superuser
            or getattr(request.user, "role", None) == "admin"
        )


class LoftViewSet(viewsets.ModelViewSet):
    queryset = Loft.objects.annotate(roll_count=Count("rolls")).all()
    serializer_class = LoftSerializer


class ClothRollViewSet(viewsets.ModelViewSet):
    serializer_class = ClothRollSerializer

    def get_queryset(self):
        qs = ClothRoll.objects.select_related("loft").all()
        loft_id = self.request.query_params.get("loftId")
        status = self.request.query_params.get("status")
        if loft_id:
            qs = qs.filter(loft_id=loft_id)
        if status:
            qs = qs.filter(status=status)
        return qs


class DipRunViewSet(viewsets.ModelViewSet):
    serializer_class = DipRunSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = DipRun.objects.select_related("roll", "roll__loft").all()
        roll_id = self.request.query_params.get("rollId")
        if roll_id:
            qs = qs.filter(roll_id=roll_id)
        # 树脂带过滤：晾晒架流水与浸渍台账共用本查询集，
        # 已设定树脂带时只放行带内记录；未设定则不过滤。
        band = ResinBand.current()
        if band is not None:
            qs = qs.filter(
                resin_pct__gte=band.lower_pct,
                resin_pct__lte=band.upper_pct,
            )
        return qs


class ResinBandView(APIView):
    """
    树脂带过滤设置（单行 singleton）。

    GET：任何登录用户可读（流水/台账展示需要）。
    PUT/POST：仅管理员。并发提交写同一行 singleton，行锁串行化后
    原地覆盖，只留一版，后提交者生效。
    """

    def get_permissions(self):
        if self.request.method in ("PUT", "POST", "PATCH", "DELETE"):
            return [IsAdminRole()]
        return [IsAuthenticated()]

    def get(self, request):
        band = ResinBand.current()
        data = ResinBandSerializer(band).data if band is not None else None
        return Response({"band": data})

    def put(self, request):
        serializer = ResinBandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        fields = {
            "lower_pct": validated["lower_pct"],
            "upper_pct": validated["upper_pct"],
            "updated_by": request.user,
            "updated_at": timezone.now(),
        }
        # 单行 singleton：先原地 UPDATE（行锁串行化并发写，后提交者覆盖先提交者）；
        # 行不存在时 INSERT，并发首插撞唯一键则退回 UPDATE。全站只留一版。
        with transaction.atomic():
            updated = ResinBand.objects.filter(pk=ResinBand.SINGLETON_PK).update(**fields)
            if not updated:
                try:
                    with transaction.atomic():
                        ResinBand.objects.create(pk=ResinBand.SINGLETON_PK, **fields)
                except IntegrityError:
                    ResinBand.objects.filter(pk=ResinBand.SINGLETON_PK).update(**fields)
        band = ResinBand.objects.get(pk=ResinBand.SINGLETON_PK)
        return Response({"band": ResinBandSerializer(band).data})

    # 兼容以 POST 提交的客户端，语义与 PUT 相同（幂等覆盖 singleton）。
    post = put


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    data = {
        "loftCount": Loft.objects.count(),
        "rawRollCount": ClothRoll.objects.filter(status=ClothRoll.STATUS_RAW).count(),
        "dippingRollCount": ClothRoll.objects.filter(
            status=ClothRoll.STATUS_DIPPING
        ).count(),
        "curedRollCount": ClothRoll.objects.filter(status=ClothRoll.STATUS_CURED).count(),
        "dipRunCount": DipRun.objects.count(),
    }
    return Response(data)
