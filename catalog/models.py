from django.db import models
from django.db.models import Sum, Q, Value, F, DecimalField
from django.db.models.functions import Coalesce


class ItemType(models.Model):
    name      = models.CharField('الاسم', max_length=50, unique=True)
    is_active = models.BooleanField('مُفعّل', default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Brand(models.Model):
    name      = models.CharField('الاسم', max_length=80, unique=True)
    is_active = models.BooleanField('مُفعّل', default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Unit(models.Model):
    name      = models.CharField('الاسم', max_length=20, unique=True)
    short     = models.CharField('الرمز', max_length=5, blank=True)
    is_active = models.BooleanField('مُفعّل', default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ItemQuerySet(models.QuerySet):
    """QuerySet مُخصص يحسب الرصيد والقيمة في قاعدة البيانات."""

    def with_balance(self):
        return (
            self.annotate(
                total_in=Coalesce(
                    Sum('movements__qty', filter=Q(movements__kind='in')),
                    Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                total_out=Coalesce(
                    Sum('movements__qty', filter=Q(movements__kind='out')),
                    Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
            )
            .annotate(balance=F('total_in') + F('opening_balance') - F('total_out'))
            .annotate(value=F('balance') * F('cost'))
        )


class Item(models.Model):
    code = models.PositiveIntegerField('كود الصنف', unique=True, null=True, blank=True)
    name       = models.CharField('اسم الصنف', max_length=150)
    type       = models.ForeignKey(ItemType, on_delete=models.PROTECT, null=True, blank=True, verbose_name='النوع')
    brand      = models.ForeignKey(Brand, on_delete=models.PROTECT,
                                   null=True, blank=True, verbose_name='البراند')
    unit       = models.ForeignKey(Unit, on_delete=models.PROTECT, null=True, blank=True, verbose_name='الوحدة')
    spec       = models.CharField('المواصفات', max_length=200, blank=True)
    min_qty    = models.DecimalField('الحد الأدنى', max_digits=10, decimal_places=2, default=0)
    cost       = models.DecimalField('سعر الشراء', max_digits=12, decimal_places=2, default=0)
    sale_price = models.DecimalField('سعر البيع', max_digits=12, decimal_places=2, default=0)
    opening_balance = models.DecimalField('رصيد أول المدة', max_digits=12, decimal_places=2, default=0)
    image = models.ImageField('الصورة', upload_to='items/', null=True, blank=True)
    notes      = models.TextField('ملاحظات', blank=True)
    is_active  = models.BooleanField('مُفعّل', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ItemQuerySet.as_manager()

    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        b = f' · {self.brand.name}' if self.brand else ''
        return f'{self.name}{b}'

    @property
    def current_qty(self):
        """الرصيد لصنف واحد — للاستخدام الفردي فقط.
        للقوائم استخدم Item.objects.with_balance()."""
        agg = self.movements.aggregate(
            ins  = Sum('qty', filter=Q(kind='in')),
            outs = Sum('qty', filter=Q(kind='out')),
        )
        return self.opening_balance + (agg['ins'] or 0) - (agg['outs'] or 0)

    @property
    def stock_value(self):
        return self.current_qty * self.cost

    @property
    def status(self):
        q = self.current_qty
        if q <= self.min_qty:       return 'bad'
        if q <= self.min_qty * 1.5: return 'warn'
        return 'ok'