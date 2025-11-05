"""
Database models for cusc_edx_api.
"""
# cusc_edx_api/models.py
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class EcommerceOrder(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"
    STATUS_CANCELED = "canceled"
    STATUS_REFUNDED = "refunded"
    STATUS_EXPIRED = "expired" 

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELED, "Canceled"),
        (STATUS_REFUNDED, "Refunded"),
        (STATUS_EXPIRED, "Expired"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="cusc_orders",
    )
    # course_id dạng string: "course-v1:org+code+run"
    course_id = models.CharField(max_length=255)

    # order id bên hệ thống Node.js (nếu có)
    external_order_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="VND")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )

    # chỗ để Node đẩy thêm info gì cũng được
    extra_data = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expired_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "cusc_ecommerce_order"
        ordering = ["-id"]

    def __str__(self):
        return f"Order #{self.id} ({self.status})"

    def to_dict(self):
        """
        Dùng để trả JSON về API cho tiện.
        """
        return {
            "id": self.id,
            "external_order_id": self.external_order_id,
            "user_id": self.user_id,
            "username": self.user.username,
            "email": self.user.email,
            "course_id": self.course_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "status": self.status,
            "extra_data": self.extra_data or {},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expired_at": self.expired_at.isoformat() if self.expired_at else None,
        }

    @classmethod
    def parse_amount(cls, value):
        """
        Hỗ trợ cả string lẫn number từ JSON Node.js gửi sang.
        """
        if value is None:
            return None
        return Decimal(str(value))
