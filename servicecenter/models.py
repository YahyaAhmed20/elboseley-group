from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from customers.models import Customer
from payroll.models import Employee


class SequenceSetting(models.Model):
    key = models.CharField(max_length=50, unique=True)
    next_number = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = 'تسلسل'
        verbose_name_plural = 'التسلسلات'

    def __str__(self):
        return f'{self.key}: {self.next_number}'


class Device(models.Model):
    code = models.PositiveIntegerField('كود الجهاز', unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='devices')
    device_type = models.CharField('نوع الجهاز', max_length=120)
    description = models.TextField('وصف الجهاز', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['code']), models.Index(fields=['device_type'])]

    def __str__(self):
        return f'جهاز #{self.code} - {self.customer.name}'


class RepairOrder(models.Model):
    class Status(models.TextChoices):
        RECEIVED = 'received', 'مستلم'
        WORKING = 'working', 'قائم على العمل'
        READY = 'ready', 'جاهز للتسليم'
        DELIVERED = 'delivered', 'تم التسليم'

    device = models.ForeignKey(Device, on_delete=models.PROTECT, related_name='repairs')
    received_at = models.DateTimeField('تاريخ ووقت الاستلام', default=timezone.now)
    fault_description = models.TextField('وصف العطل')
    deposit = models.DecimalField('العربون', max_digits=12, decimal_places=2, default=0,
                                  validators=[MinValueValidator(Decimal('0'))])
    
    paid_at_delivery = models.DecimalField(
        'المدفوع عند التسليم',
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))]
    )
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='repair_orders',
                                 null=True, blank=True)
    repair_notes = models.TextField('ما تم إصلاحه', blank=True)
    repair_date = models.DateTimeField('تاريخ الإصلاح', null=True, blank=True)
    cost = models.DecimalField('التكلفة', max_digits=12, decimal_places=2, default=0,
                               validators=[MinValueValidator(Decimal('0'))])
    labor = models.DecimalField('المصنعية', max_digits=12, decimal_places=2, default=0,
                                validators=[MinValueValidator(Decimal('0'))])
    delivered_at = models.DateTimeField('تاريخ التسليم', null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RECEIVED)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name='repair_orders_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['received_at']),
            models.Index(fields=['delivered_at']),
        ]

    def __str__(self):
        return f'صيانة #{self.pk} — جهاز {self.device.code}'

    @property
    def total(self):
        return self.cost + self.labor

    @property
    def total_paid(self):
        return self.deposit + self.paid_at_delivery

    @property
    def remaining(self):
        return max(Decimal('0'), self.total - self.total_paid)

    @property
    def profit(self):
        # التكلفة = ما تم دفعه على قطع/خامات، والمصنعية إيراد الخدمة.
        return self.labor

    def mark_work_started(self):
        self.status = self.Status.WORKING
        self.repair_date = self.repair_date or timezone.now()

    def mark_delivered(self):
        remaining = self.remaining
        self.paid_at_delivery = remaining
        self.status = self.Status.DELIVERED
        self.delivered_at = timezone.now()
