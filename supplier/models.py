from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from common.code_generator import next_code


class Supplier(models.Model):
    code = models.PositiveIntegerField(
        'كود المورد',
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )
    name = models.CharField('اسم المورد', max_length=150)
    phone = models.CharField('رقم الهاتف', max_length=50, blank=True)
    opening_balance = models.DecimalField(
        'رصيد أول المدة',
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
    )
    is_active = models.BooleanField('مُفعّل', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['phone']),
        ]

    def save(self, *args, **kwargs):
        if self.code is None:
            using = kwargs.get("using") or self._state.db or "default"
            self.code = next_code("supplier_supplier_code_seq", using)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name