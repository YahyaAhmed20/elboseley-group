from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class PurchaseInvoice(models.Model):
    class PaymentType(models.TextChoices):
        CASH = "cash", "نقدي"
        CREDIT = "credit", "آجل"
        PARTIAL = "partial", "دفع جزئي"

    supplier = models.ForeignKey(
        "supplier.Supplier",
        on_delete=models.PROTECT,
        related_name="purchase_invoices",
    )
    invoice_number = models.CharField(max_length=100)
    payment_type = models.CharField(
        max_length=10,
        choices=PaymentType.choices,
        default=PaymentType.CASH,
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_invoices",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["invoice_number"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "invoice_number"],
                name="unique_purchase_invoice_per_supplier",
            ),
        ]

    @property
    def remaining_amount(self):
        return self.total - self.paid_amount

    def __str__(self):
        return f"{self.invoice_number} - {self.supplier}"


class PurchaseInvoiceLine(models.Model):
    invoice = models.ForeignKey(
        PurchaseInvoice,
        on_delete=models.PROTECT,
        related_name="lines",
    )
    item = models.ForeignKey(
        "catalog.Item",
        on_delete=models.PROTECT,
        related_name="purchase_lines",
    )
    qty = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        ordering = ["id"]

    @property
    def line_total(self):
        return self.qty * self.unit_price

    def __str__(self):
        return f"{self.item} × {self.qty}"


class SupplierAccountEntry(models.Model):
    class EntryType(models.TextChoices):
        PURCHASE = "purchase", "فاتورة شراء"
        PAYMENT = "payment", "سداد للمورد"

    supplier = models.ForeignKey(
        "supplier.Supplier",
        on_delete=models.PROTECT,
        related_name="account_entries",
    )
    invoice = models.ForeignKey(
        PurchaseInvoice,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="account_entries",
    )
    entry_type = models.CharField(
        max_length=10,
        choices=EntryType.choices,
    )
    debit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    credit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    notes = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="supplier_account_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["supplier", "created_at"]),
        ]

    def __str__(self):
        return f"{self.supplier} - {self.get_entry_type_display()}"