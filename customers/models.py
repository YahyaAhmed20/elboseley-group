from calendar import monthrange
from datetime import date

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from decimal import Decimal

from common.code_generator import next_code


def add_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


class Customer(models.Model):
    code = models.PositiveIntegerField(
        'كود العميل',
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )
    name = models.CharField('اسم العميل', max_length=150)
    phone = models.CharField('رقم الهاتف', max_length=50, blank=True, default='')
    personal_number = models.CharField('الرقم الشخصي', max_length=100, blank=True, default='')
    car_number = models.CharField('رقم العربية', max_length=100, blank=True, default='')
    amount = models.DecimalField(
        'المبلغ', max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        default=0,
    )
    note = models.TextField('الشغل / الملاحظة', blank=True)

    follow_up_enabled = models.BooleanField('تذكير بعد 6 شهور', default=False)
    follow_up_date = models.DateField('موعد المراجعة', null=True, blank=True)
    reminder_sent_at = models.DateTimeField('آخر تذكير مُرسل', null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='customers_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['personal_number']),
            models.Index(fields=['car_number']),
            models.Index(fields=['follow_up_enabled', 'follow_up_date']),
        ]

    def save(self, *args, **kwargs):
        if self.code is None:
            using = kwargs.get("using") or self._state.db or "default"
            self.code = next_code("customers_customer_code_seq", using)
        super().save(*args, **kwargs)

    def set_follow_up(self, enabled, base_date=None):
        self.follow_up_enabled = enabled
        self.reminder_sent_at = None
        if enabled:
            base_date = base_date or (self.created_at.date() if self.created_at else date.today())
            self.follow_up_date = add_months(base_date, 6)
        else:
            self.follow_up_date = None

    def __str__(self):
        return f'{self.name} - {self.phone}'