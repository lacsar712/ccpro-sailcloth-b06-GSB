from django.conf import settings
from django.db import models


class Loft(models.Model):
    name = models.CharField(max_length=120)
    location = models.CharField(max_length=200, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class ClothRoll(models.Model):
    STATUS_RAW = "raw"
    STATUS_DIPPING = "dipping"
    STATUS_CURED = "cured"
    STATUS_CHOICES = [
        (STATUS_RAW, "原布"),
        (STATUS_DIPPING, "浸渍中"),
        (STATUS_CURED, "已固化"),
    ]

    loft = models.ForeignKey(Loft, on_delete=models.CASCADE, related_name="rolls")
    roll_code = models.CharField(max_length=40)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RAW)
    fabric_weight_gsm = models.PositiveIntegerField(default=380)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["loft_id", "roll_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["loft", "roll_code"],
                name="uniq_roll_code_per_loft",
            )
        ]

    def __str__(self):
        return f"{self.loft.name}/{self.roll_code}"


class DipRun(models.Model):
    roll = models.ForeignKey(ClothRoll, on_delete=models.CASCADE, related_name="dip_runs")
    started_at = models.DateTimeField()
    resin_pct = models.DecimalField(max_digits=5, decimal_places=2)
    cure_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Dip@{self.roll_id} {self.started_at}"


class ResinBand(models.Model):
    """
    树脂带过滤设置（单行 singleton）。

    全站只保留一版：保存即原地更新 pk=SINGLETON_PK 的行，
    并发提交时后提交者覆盖先提交者，流水与台账读取同一行。
    仅作显示过滤，不回写任何 DipRun.resin_pct。
    """

    SINGLETON_PK = 1

    lower_pct = models.DecimalField(max_digits=5, decimal_places=2)
    upper_pct = models.DecimalField(max_digits=5, decimal_places=2)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"树脂带 {self.lower_pct}% ~ {self.upper_pct}%"

    @classmethod
    def current(cls):
        """当前生效的树脂带；未设定时返回 None（不过滤）。"""
        return cls.objects.filter(pk=cls.SINGLETON_PK).first()
