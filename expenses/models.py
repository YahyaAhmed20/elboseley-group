from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from payroll.models import Employee
from finance.models import Account

class ExpenseCategory(models.Model):
    name = models.CharField('البند', max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="expense_categories",
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Expense(models.Model):
    beneficiary = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='expenses')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name='expenses')
    amount = models.DecimalField('التكلفة', max_digits=12, decimal_places=2,
                                 validators=[MinValueValidator(Decimal('0.01'))])
    expense_date = models.DateField('التاريخ')
    note = models.TextField('ملاحظة', blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    is_cancelled = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-expense_date', '-created_at']
        indexes = [models.Index(fields=['expense_date']), models.Index(fields=['beneficiary', 'category'])]

    def __str__(self):
        return f'{self.beneficiary} - {self.amount}'