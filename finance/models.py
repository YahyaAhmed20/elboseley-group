from django.db import models

# Create your models here.
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class FinancialTransaction(models.Model):
    class Type(models.TextChoices):
        INCOME = 'income', 'إيراد'
        EXPENSE = 'expense', 'مصروف'

    transaction_type = models.CharField(
        'نوع الحركة',
        max_length=10,
        choices=Type.choices,
    )

    amount = models.DecimalField(
        'المبلغ',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )

    description = models.CharField(
        'البيان',
        max_length=255,
    )

    repair_order = models.ForeignKey(
        'servicecenter.RepairOrder',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='financial_transactions',
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='financial_transactions',
    )

    created_at = models.DateTimeField(
        'التاريخ',
        auto_now_add=True,
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['repair_order']),
        ]

    def __str__(self):
        return f'{self.get_transaction_type_display()} - {self.amount} ج.م'