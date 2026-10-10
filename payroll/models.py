from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce
from decimal import Decimal
from django.core.exceptions import ValidationError


class Employee(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'يعمل'
        INACTIVE = 'inactive', 'متوقف'

    name = models.CharField('اسم الموظف', max_length=150)
    phone = models.CharField('رقم الهاتف', max_length=50, blank=True, default='')
    national_id = models.CharField('رقم البطاقة', max_length=30, blank=True, default='')
    salary = models.DecimalField(
        'المرتب الشهري', max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
    )
    start_date = models.DateField('تاريخ بداية العمل', null=True, blank=True)
    status = models.CharField('الحالة', max_length=10, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['name']), models.Index(fields=['status'])]

    def __str__(self):
        return self.name


class PayrollMonth(models.Model):
    year = models.PositiveSmallIntegerField('السنة')
    month = models.PositiveSmallIntegerField('الشهر')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-year', '-month']
        constraints = [
            models.UniqueConstraint(fields=['year', 'month'], name='unique_payroll_month'),
            models.CheckConstraint(condition=models.Q(month__gte=1, month__lte=12), name='valid_payroll_month'),
        ]

    def __str__(self):
        return f'{self.year:04d}-{self.month:02d}'

    @property
    def label(self):
        months = [
            'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
            'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر',
        ]
        return f'{months[self.month - 1]} {self.year}'


class EmployeePayroll(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='payrolls')
    payroll_month = models.ForeignKey(PayrollMonth, on_delete=models.PROTECT, related_name='employee_payrolls')
    salary = models.DecimalField(
        'مرتب الشهر', max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['employee__name']
        constraints = [
            models.UniqueConstraint(fields=['employee', 'payroll_month'], name='unique_employee_payroll_month')
        ]
        indexes = [models.Index(fields=['payroll_month', 'employee'])]

    def __str__(self):
        return f'{self.employee} - {self.payroll_month}'

    def _total_kind(self, kind):
        return self.transactions.filter(kind=kind).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0'))
        )['total'] or Decimal('0')

    @property
    def total_advance(self):
        return self._total_kind(PayrollTransaction.Kind.ADVANCE)

    @property
    def total_waste(self):
        return self._total_kind(PayrollTransaction.Kind.WASTE)

    @property
    def total_other(self):
        return self._total_kind(PayrollTransaction.Kind.OTHER)

    @property
    def total_deductions(self):
        return self.total_advance + self.total_waste + self.total_other

    @property
    def net_salary(self):
        return self.salary - self.total_deductions


class PayrollTransaction(models.Model):
    class Kind(models.TextChoices):
        ADVANCE = 'advance', 'سلفة'
        WASTE = 'waste', 'هدر'
        OTHER = 'other', 'خصم آخر'

    employee_payroll = models.ForeignKey(
        EmployeePayroll, on_delete=models.PROTECT, related_name='transactions'
    )
    kind = models.CharField('النوع', max_length=10, choices=Kind.choices)
    amount = models.DecimalField(
        'المبلغ', max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    note = models.TextField('الملاحظة', blank=True)
    transaction_date = models.DateField('التاريخ')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.employee_payroll_id and self.transaction_date:
            month = self.employee_payroll.payroll_month
            if (self.transaction_date.year, self.transaction_date.month) != (month.year, month.month):
                raise ValidationError({'transaction_date': 'تاريخ العملية يجب أن يكون داخل شهر المرتب المحدد.'})

    class Meta:
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['employee_payroll', 'kind']),
            models.Index(fields=['transaction_date']),
        ]

    def __str__(self):
        return f'{self.employee_payroll.employee} - {self.amount}'
