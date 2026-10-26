from decimal import Decimal, InvalidOperation

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.utils import timezone
from finance.services import validate_cashbox_expense
from catalog.models import Item
from finance.models import CashboxTransaction
from inventory.models import StockMovement
from supplier.models import Supplier
from finance.services import (
    validate_cashbox_expense,
    ensure_default_accounts,
    create_journal_entry,
)


from .models import (
    PurchaseInvoice,
    PurchaseInvoiceLine,
    SupplierAccountEntry,
)


def to_decimal(value, field_name):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(f"{field_name} يجب أن يكون رقمًا صحيحًا.")

    if not result.is_finite():
        raise ValidationError(f"{field_name} يجب أن يكون رقمًا صالحًا.")

    return result


@transaction.atomic
def create_purchase_invoice(
    *,
    supplier_id,
    invoice_number,
    payment_type,
    lines,
    paid_amount,
    notes="",
    user,
):
    """
    Create a purchase invoice and its stock movements atomically.

    Each line is a dict with:
        item_id, qty, unit_price
    """
    invoice_number = str(invoice_number).strip()
    if not invoice_number:
        raise ValidationError("Invoice number is required.")

    
    if not isinstance(lines, (list, tuple)) or not 1 <= len(lines) <= 10:
        raise ValidationError("An invoice must contain 1 to 10 items.")

    if any(not isinstance(line, dict) for line in lines):
        raise ValidationError("Each invoice line must be a valid object.")

    item_ids = [line.get("item_id") for line in lines]

    if any(item_id in (None, "") for item_id in item_ids):
        raise ValidationError("Every invoice line must include an item.")

    if len(set(map(str, item_ids))) != len(item_ids):
        raise ValidationError("Each item can appear only once on an invoice.")


    try:
        supplier = Supplier.objects.select_for_update().get(
            pk=supplier_id,
            is_active=True,
        )
    except (Supplier.DoesNotExist, ValueError, TypeError):
        raise ValidationError("المورد غير موجود أو غير نشط.")

    normalized_lines = []
    total = Decimal("0.00")

    for line in lines:
        item_id = line.get("item_id")
        qty = to_decimal(line.get("qty", "0"), "الكمية")
        unit_price = to_decimal(line.get("unit_price", "0"), "سعر الوحدة")

        if qty <= 0:
            raise ValidationError("Quantity must be greater than zero.")

        if unit_price < 0:
            raise ValidationError("Unit price cannot be negative.")

        try:
            item = Item.objects.select_for_update().get(
                pk=item_id,
                is_active=True,
            )
        except (Item.DoesNotExist, ValueError, TypeError):
            raise ValidationError("الصنف غير موجود أو غير نشط.")

        line_total = qty * unit_price
        total += line_total

        normalized_lines.append({
            "item": item,
            "qty": qty,
            "unit_price": unit_price,
            "line_total": line_total,
        })

    paid_amount = to_decimal(paid_amount, "المبلغ المدفوع")
    if paid_amount < 0 or paid_amount > total:
        raise ValidationError(
            "Paid amount must be between zero and the invoice total."
        )

    if payment_type == PurchaseInvoice.PaymentType.CASH:
        if paid_amount != total:
            raise ValidationError(
                "A cash invoice must be paid in full."
            )
    elif payment_type == PurchaseInvoice.PaymentType.CREDIT:
        if paid_amount != 0:
            raise ValidationError(
                "A credit invoice cannot have a payment at creation."
            )
    elif payment_type == PurchaseInvoice.PaymentType.PARTIAL:
        if not (Decimal("0.00") < paid_amount < total):
            raise ValidationError(
                "A partial payment must be greater than zero "
                "and less than the invoice total."
            )
    else:
        raise ValidationError("Invalid payment type.")

    if paid_amount > 0:
        validate_cashbox_expense(paid_amount)

    invoice = PurchaseInvoice.objects.create(
        supplier=supplier,
        invoice_number=invoice_number,
        payment_type=payment_type,
        total=total,
        paid_amount=paid_amount,
        notes=notes,
        created_by=user,
    )

    if paid_amount > 0:
        CashboxTransaction.objects.create(
            kind=CashboxTransaction.Kind.EXPENSE,
            amount=paid_amount,
            description=f"Purchase invoice #{invoice_number}",
            purchase_invoice=invoice,
            created_by=user,
        )

    for line_data in normalized_lines:
        item = line_data["item"]

        invoice_line = PurchaseInvoiceLine.objects.create(
            invoice=invoice,
            item=item,
            qty=line_data["qty"],
            unit_price=line_data["unit_price"],
        )

        StockMovement.objects.create(
            kind=StockMovement.Kind.IN,
            item=item,
            purchase_line=invoice_line,
            qty=line_data["qty"],
            ref=invoice_number[:50],
            notes=f"Purchase invoice #{invoice_number}",
            created_by=user,
        )

        item.cost = line_data["unit_price"]
        item.save(update_fields=["cost"])

    SupplierAccountEntry.objects.create(
        supplier=supplier,
        invoice=invoice,
        entry_type=SupplierAccountEntry.EntryType.PURCHASE,
        debit=Decimal("0.00"),
        credit=total,
        notes=f"Purchase invoice #{invoice_number}",
        created_by=user,
    )

    if paid_amount > 0:
        SupplierAccountEntry.objects.create(
            supplier=supplier,
            invoice=invoice,
            entry_type=SupplierAccountEntry.EntryType.PAYMENT,
            debit=paid_amount,
            credit=Decimal("0.00"),
            notes=f"Payment for invoice #{invoice_number}",
            created_by=user,
        )

    accounts = ensure_default_accounts()

    journal_lines = [
        {
            "account_id": accounts["1200"].pk,
            "debit": total,
            "credit": Decimal("0.00"),
            "description": f"إثبات مشتريات {invoice_number}",
        },
    ]

    if paid_amount > 0:
        journal_lines.append({
            "account_id": accounts["1000"].pk,
            "debit": Decimal("0.00"),
            "credit": paid_amount,
            "description": f"المبلغ المدفوع نقدًا {invoice_number}",
        })

    remaining_amount = total - paid_amount

    if remaining_amount > 0:
        journal_lines.append({
            "account_id": accounts["2000"].pk,
            "debit": Decimal("0.00"),
            "credit": remaining_amount,
            "description": f"المتبقي للمورد {invoice_number}",
        })

    create_journal_entry(
        entry_number=f"PUR-{invoice.pk}",
        entry_date=timezone.localdate(),
        description=f"فاتورة مشتريات رقم {invoice_number}",
        reference_type="purchase_invoice",
        reference_id=invoice.pk,
        user=user,
        lines=journal_lines,
    )

    return invoice





@transaction.atomic
def pay_purchase_invoice(*, invoice_id, amount, user, notes=""):
    """Record a supplier payment against an existing purchase invoice."""
    try:
        amount = to_decimal(amount, "المبلغ المدفوع").quantize(
            Decimal("0.01")
        )
    except ValidationError:
        raise

    if amount <= Decimal("0.00"):
        raise ValidationError("المبلغ المدفوع يجب أن يكون أكبر من صفر.")

    try:
        invoice = (
            PurchaseInvoice.objects.select_for_update()
            .select_related("supplier")
            .get(pk=invoice_id)
        )
    except PurchaseInvoice.DoesNotExist:
        raise ValidationError("فاتورة الشراء غير موجودة.")

    if not user or not getattr(user, "is_authenticated", False):
        raise ValidationError("يجب تحديد مستخدم مسجل الدخول.")

    remaining = invoice.remaining_amount

    if remaining <= Decimal("0.00"):
        raise ValidationError("الفاتورة مسددة بالكامل.")

    if amount > remaining:
        raise ValidationError(
            f"المبلغ أكبر من المتبقي على الفاتورة ({remaining:.2f})."
        )

    validate_cashbox_expense(amount)

    accounts = ensure_default_accounts()

    new_paid_amount = invoice.paid_amount + amount
    invoice.paid_amount = new_paid_amount

    if new_paid_amount == invoice.total:
        invoice.payment_type = PurchaseInvoice.PaymentType.CASH
    elif new_paid_amount > Decimal("0.00"):
        invoice.payment_type = PurchaseInvoice.PaymentType.PARTIAL

    invoice.save(update_fields=["paid_amount", "payment_type"])

    payment = CashboxTransaction.objects.create(
        kind=CashboxTransaction.Kind.EXPENSE,
        amount=amount,
        description=f"سداد للمورد عن فاتورة #{invoice.invoice_number}",
        purchase_invoice=invoice,
        created_by=user,
    )

    SupplierAccountEntry.objects.create(
        supplier=invoice.supplier,
        invoice=invoice,
        entry_type=SupplierAccountEntry.EntryType.PAYMENT,
        debit=amount,
        credit=Decimal("0.00"),
        notes=notes or f"سداد لاحق للفاتورة #{invoice.invoice_number}",
        created_by=user,
    )

    create_journal_entry(
        entry_number=f"PAY-{payment.pk}",
        entry_date=timezone.localdate(),
        description=f"سداد فاتورة مشتريات #{invoice.invoice_number}",
        reference_type="purchase_payment",
        reference_id=payment.pk,
        user=user,
        lines=[
            {
                "account_id": accounts["2000"].pk,
                "debit": amount,
                "credit": Decimal("0.00"),
                "description": "تخفيض مديونية المورد",
            },
            {
                "account_id": accounts["1000"].pk,
                "debit": Decimal("0.00"),
                "credit": amount,
                "description": "صرف من الخزنة",
            },
        ],
    )

    return payment
