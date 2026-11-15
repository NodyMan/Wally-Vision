from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Finding(models.Model):
    STATUS_NEW = "new"
    STATUS_REVIEWED = "reviewed"
    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_REVIEWED, "Reviewed"),
    ]

    ra = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(360.0)]
    )
    dec = models.FloatField(
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)]
    )
    note = models.CharField(max_length=500)
    nickname = models.CharField(max_length=80, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    ip_hash = models.CharField(max_length=64, db_index=True)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_NEW
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        label = self.nickname or "Anonymous"
        return f"Finding #{self.pk} ({self.ra:.4f}, {self.dec:.4f}) by {label}"
