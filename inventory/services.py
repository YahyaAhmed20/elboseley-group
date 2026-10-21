from decimal import Decimal
from django.db import transaction
from .models import StockMovement, StockIssue, StockIssueLine
from django.core.exceptions import ValidationError
from django.db import transaction

from catalog.models import Item
from .models import StockMovement


@transaction.atomic
def create_movement(*, item_id, kind, qty, ref='', notes='', user):
    qty = Decimal(str(qty))

    if qty <= 0:
        raise ValidationError('الكمية يجب أن تكون أكبر من صفر.')

    item = Item.objects.select_for_update().get(pk=item_id)

    if kind == StockMovement.Kind.OUT and qty > item.current_qty:
        unit_name = item.unit.name if item.unit else ""
        raise ValidationError(
            f"المتاح {item.current_qty} {unit_name} فقط."
        )

    return StockMovement.objects.create(
        item=item,
        kind=kind,
        qty=qty,
        ref=ref,
        notes=notes,
        created_by=user,
    )


@transaction.atomic
def update_movement(
    *,
    movement_id,
    item_id,
    kind,
    qty,
    ref='',
    notes='',
):
    qty = Decimal(str(qty))

    if qty <= 0:
        raise ValidationError('الكمية يجب أن تكون أكبر من صفر.')

    movement = (
        StockMovement.objects
        .select_for_update()
        .get(pk=movement_id)
    )

    if movement.purchase_line_id is not None:
        raise ValidationError(
            "لا يمكن تعديل حركة مخزون مرتبطة بفاتورة شراء."
        )
    if movement.issue_line_id is not None:
        raise ValidationError(
            "لا يمكن تعديل حركة مخزون مرتبطة بفاتورة صرف."
        )

    old_item_id = movement.item_id

    # نقفل الصنف القديم والجديد.
    item_ids = sorted({old_item_id, item_id})

    locked_items = {
        item.pk: item
        for item in Item.objects
        .select_for_update()
        .filter(pk__in=item_ids)
    }

    old_item = locked_items[old_item_id]
    new_item = locked_items[item_id]

    # الرصيد المتاح للصنف الجديد بعد استبعاد تأثير الحركة الحالية
    available = new_item.current_qty

    if new_item.pk == old_item.pk:
        if movement.kind == StockMovement.Kind.IN:
            available -= movement.qty
        else:
            available += movement.qty

    if kind == StockMovement.Kind.OUT and qty > available:
        unit_name = new_item.unit.name if new_item.unit else ""
        raise ValidationError(
            f"المتاح {available} {unit_name} فقط."
        )

    movement.item = new_item
    movement.kind = kind
    movement.qty = qty
    movement.ref = ref
    movement.notes = notes

    movement.save(
        update_fields=[
            'item',
            'kind',
            'qty',
            'ref',
            'notes',
        ]
    )

    return movement


@transaction.atomic
def delete_movement(*, movement_id):
    movement = (
        StockMovement.objects
        .select_for_update()
        .get(pk=movement_id)
    )

    if movement.purchase_line_id is not None:
        raise ValidationError(
            "لا يمكن حذف حركة مخزون مرتبطة بفاتورة شراء."
        )

    if movement.issue_line_id is not None:
        raise ValidationError(
            "لا يمكن حذف حركة مخزون مرتبطة بفاتورة صرف."
        )

    Item.objects.select_for_update().get(pk=movement.item_id)

    movement.delete()


@transaction.atomic
def create_stock_issue(
    *,
    invoice_number,
    recipient,
    issue_type,
    lines,
    notes="",
    user,
):
    invoice_number = str(invoice_number).strip()
    recipient = str(recipient).strip()

    if not invoice_number:
        raise ValidationError("رقم فاتورة الصرف مطلوب.")

    if not recipient:
        raise ValidationError("اسم المستلم مطلوب.")

    if issue_type not in StockIssue.IssueType.values:
        raise ValidationError("نوع الصرف غير صحيح.")

    if not isinstance(lines, (list, tuple)) or not 1 <= len(lines) <= 10:
        raise ValidationError("يجب أن تحتوي الفاتورة على صنف واحد إلى 10 أصناف.")

    item_ids = [line.get("item_id") for line in lines if isinstance(line, dict)]

    if len(item_ids) != len(lines) or any(
        item_id in (None, "") for item_id in item_ids
    ):
        raise ValidationError("كل بند يجب أن يحتوي على صنف صحيح.")

    if len(set(map(str, item_ids))) != len(item_ids):
        raise ValidationError("لا يمكن تكرار الصنف نفسه في الفاتورة.")

    normalized_lines = []

    # قفل الأصناف بترتيب ثابت لتقليل احتمال التعارض بين العمليات المتزامنة.
    items = {
        item.pk: item
        for item in Item.objects.select_for_update()
        .filter(pk__in=item_ids, is_active=True)
        .order_by("pk")
    }

    if len(items) != len(set(map(str, item_ids))):
        raise ValidationError("يوجد صنف غير موجود أو غير نشط.")

    for line in lines:
        try:
            qty = Decimal(str(line.get("qty", "0")))
            unit_price = Decimal(str(line.get("unit_price", "0")))
        except Exception:
            raise ValidationError("الكمية والسعر يجب أن يكونا أرقامًا صحيحة.")

        if not qty.is_finite() or qty <= 0:
            raise ValidationError("الكمية يجب أن تكون أكبر من صفر.")

        if not unit_price.is_finite() or unit_price < 0:
            raise ValidationError("السعر لا يمكن أن يكون سالبًا.")

        item = items[int(line["item_id"])]

        available = item.current_qty
        if qty > available:
            unit_name = item.unit.name if item.unit else ""
            raise ValidationError(
                f"الصنف {item.name}: المتاح {available} {unit_name} فقط."
            )

        normalized_lines.append({
            "item": item,
            "qty": qty,
            "unit_price": unit_price,
        })

    issue = StockIssue.objects.create(
        invoice_number=invoice_number,
        recipient=recipient,
        issue_type=issue_type,
        notes=notes,
        created_by=user,
    )

    for line in normalized_lines:
        issue_line = StockIssueLine.objects.create(
            issue=issue,
            item=line["item"],
            qty=line["qty"],
            unit_price=line["unit_price"],
        )

        StockMovement.objects.create(
            kind=StockMovement.Kind.OUT,
            item=line["item"],
            issue_line=issue_line,
            qty=line["qty"],
            ref=invoice_number[:50],
            notes=f"فاتورة صرف #{invoice_number}",
            created_by=user,
        )

    return issue


@transaction.atomic
def update_stock_issue(
    *,
    issue_id,
    invoice_number,
    recipient,
    issue_type,
    lines,
    notes="",
):
    invoice_number = str(invoice_number).strip()
    recipient = str(recipient).strip()

    if not invoice_number or not recipient:
        raise ValidationError("رقم الفاتورة واسم المستلم مطلوبان.")

    if issue_type not in StockIssue.IssueType.values:
        raise ValidationError("نوع الصرف غير صحيح.")

    if not isinstance(lines, (list, tuple)) or not 1 <= len(lines) <= 10:
        raise ValidationError("يجب أن تحتوي الفاتورة على بند واحد إلى 10 بنود.")

    item_ids = [line.get("item_id") for line in lines]
    if any(value in (None, "") for value in item_ids):
        raise ValidationError("كل بند يجب أن يحتوي على صنف صحيح.")

    if len(set(map(str, item_ids))) != len(item_ids):
        raise ValidationError("لا يمكن تكرار الصنف في الفاتورة.")

    issue = StockIssue.objects.select_for_update().get(pk=issue_id)

    if StockIssue.objects.filter(invoice_number=invoice_number).exclude(
        pk=issue.pk
    ).exists():
        raise ValidationError({"invoice_number": "رقم الفاتورة مستخدم بالفعل."})

    old_lines = list(
        issue.lines.select_related("item").prefetch_related("stock_movement")
    )

    # حساب الرصيد المتاح بعد استبعاد صرف الفاتورة الحالية.
    old_qty_by_item = {}
    for old_line in old_lines:
        old_qty_by_item[old_line.item_id] = (
            old_qty_by_item.get(old_line.item_id, Decimal("0"))
            + old_line.qty
        )

    normalized = []
    items = {
        item.pk: item
        for item in Item.objects.select_for_update()
        .filter(pk__in=item_ids, is_active=True)
        .order_by("pk")
    }

    if len(items) != len(set(map(str, item_ids))):
        raise ValidationError("يوجد صنف غير موجود أو غير نشط.")

    for line in lines:
        try:
            item_id = int(line["item_id"])
            qty = Decimal(str(line["qty"]))
            price = Decimal(str(line.get("unit_price", "0")))
        except (ValueError, TypeError, KeyError, ArithmeticError):
            raise ValidationError("الكمية والسعر يجب أن يكونا أرقامًا صحيحة.")

        if not qty.is_finite() or qty <= 0:
            raise ValidationError("الكمية يجب أن تكون أكبر من صفر.")

        if not price.is_finite() or price < 0:
            raise ValidationError("السعر لا يمكن أن يكون سالبًا.")

        item = items.get(item_id)
        if item is None:
            raise ValidationError("يوجد صنف غير صالح.")

        available = item.current_qty + old_qty_by_item.get(item_id, Decimal("0"))
        if qty > available:
            raise ValidationError(
                f"الصنف {item.name}: المتاح بعد استبعاد الفاتورة الحالية "
                f"{available} فقط."
            )

        normalized.append({
            "item": item,
            "qty": qty,
            "unit_price": price,
        })

    # حذف الحركات القديمة والبنود داخل نفس المعاملة.
    StockMovement.objects.filter(issue_line__issue=issue).delete()
    issue.lines.all().delete()

    issue.invoice_number = invoice_number
    issue.recipient = recipient
    issue.issue_type = issue_type
    issue.notes = notes
    issue.save(update_fields=[
        "invoice_number", "recipient", "issue_type", "notes"
    ])

    for line in normalized:
        issue_line = StockIssueLine.objects.create(
            issue=issue,
            item=line["item"],
            qty=line["qty"],
            unit_price=line["unit_price"],
        )
        StockMovement.objects.create(
            kind=StockMovement.Kind.OUT,
            item=line["item"],
            issue_line=issue_line,
            qty=line["qty"],
            ref=invoice_number[:50],
            notes=f"فاتورة صرف #{invoice_number}",
            created_by=issue.created_by,
        )

    return issue


@transaction.atomic
def delete_stock_issue(*, issue_id):
    issue = StockIssue.objects.select_for_update().get(pk=issue_id)

    StockMovement.objects.filter(issue_line__issue=issue).delete()
    issue.lines.all().delete()
    issue.delete()