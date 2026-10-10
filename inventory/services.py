from decimal import Decimal

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
        raise ValidationError(
            f'المتاح {item.current_qty} {item.unit.name} فقط.'
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
        raise ValidationError(
            f'المتاح {available} {new_item.unit.name} فقط.'
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

    Item.objects.select_for_update().get(pk=movement.item_id)

    movement.delete()