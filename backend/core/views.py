from django.db.models import Count
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ClothRoll, DipRun, Loft
from .rules import get_resin_band, save_resin_band
from .serializers import (
    ClothRollSerializer,
    DipRunSerializer,
    LoftSerializer,
    ResinBandSerializer,
)


class IsAdminRole(BasePermission):
    message = "仅管理员可设置树脂带"

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and getattr(user, "role", None) == "admin"
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
        # 树脂带过滤：晾晒架流水与浸渍台账共用同一接口，天然同一套带；
        # 仅按树脂百分比筛选返回，绝不改动任何 DipRun 的 resin_pct。
        band = get_resin_band()
        if band is not None:
            qs = qs.filter(
                resin_pct__gte=band.lower_pct,
                resin_pct__lte=band.upper_pct,
            )
        return qs


class ResinBandView(APIView):
    """树脂带过滤设置：GET 任意登录用户可读；写操作仅管理员。"""

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminRole()]

    def get(self, request):
        band = get_resin_band()
        if band is None:
            # 明确的 JSON null：未设置树脂带（不过滤）
            return JsonResponse(None, safe=False)
        return Response(ResinBandSerializer(band).data)

    def put(self, request):
        serializer = ResinBandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        band = save_resin_band(
            lower_pct=serializer.validated_data["lower_pct"],
            upper_pct=serializer.validated_data["upper_pct"],
            user=request.user,
        )
        return Response(ResinBandSerializer(band).data)

    # 兼容 POST 提交，语义与 PUT 相同（整版覆盖）
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
