"""帆布浸渍防水台业务规则。"""

from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, OperationalError, transaction

from .models import ClothRoll, DipRun, ResinBand

MIN_CURE_HOURS_FOR_CURED = Decimal("12")


def latest_dip_run(roll: ClothRoll) -> DipRun | None:
    return roll.dip_runs.order_by("-started_at", "-id").first()


def can_mark_roll_cured(roll: ClothRoll) -> tuple[bool, str]:
    """
    布卷转为「已固化」(cured) 的前提：
    最近一条浸渍记录的固化时长已记录，且 >= 12 小时。
    """
    latest = latest_dip_run(roll)
    if latest is None:
        return False, "该布卷尚无浸渍记录，不能标记为已固化"
    if latest.cure_hours is None:
        return False, "最近浸渍记录尚未填写固化时长，不能标记为已固化"
    if latest.cure_hours < MIN_CURE_HOURS_FOR_CURED:
        return (
            False,
            f"最近浸渍固化时长 {latest.cure_hours} 小时低于 {MIN_CURE_HOURS_FOR_CURED} 小时，不能标记为已固化",
        )
    return True, ""


def get_resin_band() -> ResinBand | None:
    """读取当前树脂带；未设置时返回 None（不过滤）。"""
    return ResinBand.objects.order_by("pk").first()


def save_resin_band(lower_pct, upper_pct, user=None) -> ResinBand:
    """
    保存树脂带（单行原子写）。

    下限/上限作为同一行的一次 UPDATE 落库：两人几乎同时提交两套不同上下限时，
    后提交的事务整行覆盖先提交的，库里永远只留一版，不会出现下限来自 A、
    上限来自 B 的撕裂状态。浸渍流水与台账读取的都是这同一行。
    """
    last_error = None
    for _attempt in range(5):
        try:
            with transaction.atomic():
                band = ResinBand.objects.select_for_update().order_by("pk").first()
                if band is not None:
                    # 兜底收敛：若历史上意外存在多行，只留最早一行
                    ResinBand.objects.exclude(pk=band.pk).delete()
                    band.lower_pct = lower_pct
                    band.upper_pct = upper_pct
                    band.updated_by = user
                    band.save(
                        update_fields=["lower_pct", "upper_pct", "updated_by", "updated_at"]
                    )
                    return band
                try:
                    # 固定主键：并发首次创建时只有一方能插入，另一方整行重试为更新
                    with transaction.atomic():
                        return ResinBand.objects.create(
                            pk=1,
                            lower_pct=lower_pct,
                            upper_pct=upper_pct,
                            updated_by=user,
                        )
                except IntegrityError:
                    continue
        except OperationalError as exc:
            # 行锁等待/死锁/SQLite 写锁等瞬时冲突：回滚后整版重试
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    band = ResinBand.objects.order_by("pk").first()
    if band is None:  # 理论上不可达
        raise RuntimeError("树脂带保存失败")
    return band
