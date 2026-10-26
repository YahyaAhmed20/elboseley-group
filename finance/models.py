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
    
    
    

class CashboxTransaction(models.Model):
    class Kind(models.TextChoices):
        INCOME = "income", "إيداع"
        EXPENSE = "expense", "صرف"
        OPENING = "opening", "رصيد افتتاحي"

    kind = models.CharField(
        max_length=10,
        choices=Kind.choices,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    description = models.CharField(max_length=255)
    purchase_invoice = models.ForeignKey(
        "purchases.PurchaseInvoice",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cashbox_transactions",
    )
    expense = models.OneToOneField(
        "expenses.Expense",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cashbox_transaction",
    )
    is_reversal = models.BooleanField(default=False)
    reverses = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reversal_transaction",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cashbox_transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["kind", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} - {self.amount}"





class Account(models.Model):
    class AccountType(models.TextChoices):
        ASSET = "asset", "أصول"
        LIABILITY = "liability", "التزامات"
        EQUITY = "equity", "حقوق ملكية"
        REVENUE = "revenue", "إيرادات"
        EXPENSE = "expense", "مصروفات"

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class JournalEntry(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "مسودة"
        POSTED = "posted", "مُرحّل"
        REVERSED = "reversed", "معكوس"

    entry_number = models.CharField(max_length=30, unique=True)
    entry_date = models.DateField()
    description = models.CharField(max_length=255)
    reference_type = models.CharField(max_length=50, blank=True)
    reference_id = models.PositiveBigIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="journal_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-entry_date", "-id"]
        indexes = [
            models.Index(fields=["entry_date", "status"]),
            models.Index(fields=["reference_type", "reference_id"]),
        ]

    def __str__(self):
        return f"{self.entry_number} - {self.description}"


class JournalLine(models.Model):
    entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.PROTECT,
        related_name="lines",
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="journal_lines",
    )
    debit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    credit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["account", "entry"]),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.debit < 0 or self.credit < 0:
            raise ValidationError("المبلغ لا يمكن أن يكون سالبًا.")

        if (self.debit > 0 and self.credit > 0) or (
            self.debit == 0 and self.credit == 0
        ):
            raise ValidationError(
                "يجب تحديد مدين أو دائن فقط لكل سطر."
            )

    def __str__(self):
        return f"{self.entry.entry_number} - {self.account.code}"