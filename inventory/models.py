from django.db import models
from decimal import Decimal
# Create your models here.
# inventory/models.py
from django.db import models
from django.conf import settings
from catalog.models import Item

class StockMovement(models.Model):
    class Kind(models.TextChoices):
        IN  = 'in',  'استلام'
        OUT = 'out', 'صرف'

    kind       = models.CharField(max_length=3, choices=Kind.choices)
    item       = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='movements')
    purchase_line = models.OneToOneField(
        "purchases.PurchaseInvoiceLine",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_movement",
    )
    issue_line = models.OneToOneField(
        "inventory.StockIssueLine",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_movement",
    )
    qty        = models.DecimalField(max_digits=10, decimal_places=2)
    ref        = models.CharField(max_length=50, blank=True)
    notes      = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['item', 'kind'])]
        
        
        

class StockIssue(models.Model):
    class IssueType(models.TextChoices):
        SALE = "sale", "بيع"
        TECHNICIAN = "technician", "تسليم لفني"
        INTERNAL = "internal", "استخدام داخلي"
        SUPPLIER_RETURN = "supplier_return", "مرتجع للمورد"

    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="رقم فاتورة الصرف",
    )
    recipient = models.CharField(
        max_length=150,
        verbose_name="المستلم",
    )
    issue_type = models.CharField(
        max_length=20,
        choices=IssueType.choices,
        verbose_name="نوع الصرف",
    )
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_issues",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.invoice_number

    @property
    def total(self):
        return sum(
            (line.qty * line.unit_price for line in self.lines.all()),
            Decimal("0.00"),
        )


class StockIssueLine(models.Model):
    issue = models.ForeignKey(
        StockIssue,
        on_delete=models.PROTECT,
        related_name="lines",
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name="stock_issue_lines",
    )
    qty = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.item} × {self.qty}"
