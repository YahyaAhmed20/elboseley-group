from decimal import Decimal
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.shortcuts import render, redirect, get_object_or_404
from accounts.decorators import require_perm
from .models import Item, ItemType, Brand
from .forms import ItemForm
from servicecenter.models import SequenceSetting
from django.db import transaction

SORT_MAP = {
    'name':    'name',
    '-name':   '-name',
    'qty':     'balance',
    '-qty':    '-balance',
    'value':   'value',
    '-value':  '-value',
    'cost':    'cost',
    '-cost':   '-cost',
}


def item_list(request):
    q        = request.GET.get('q', '').strip()
    type_id  = request.GET.get('type', '').strip()
    brand_id = request.GET.get('brand', '').strip()
    status   = request.GET.get('status', '').strip()
    sort     = request.GET.get('sort', 'name').strip()

    items = Item.objects.filter(is_active=True).select_related('brand', 'type', 'unit').with_balance()

    if q:
        if q.isdigit():
            items = items.filter(code=int(q))
        else:
            items = items.filter(
                Q(name__icontains=q) |
                Q(brand__name__icontains=q) |
                Q(type__name__icontains=q)
            )
    if type_id:
        items = items.filter(type_id=type_id)
    if brand_id:
        items = items.filter(brand_id=brand_id)

    factor = Decimal('1.5')
    if status == 'ok':
        items = items.filter(balance__gt=F('min_qty') * factor)
    elif status == 'warn':
        items = items.filter(balance__lte=F('min_qty') * factor,
                             balance__gt=F('min_qty'))
    elif status == 'bad':
        items = items.filter(balance__lte=F('min_qty'))

    items = items.order_by(SORT_MAP.get(sort, 'name'))

    paginator = Paginator(items, 20)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'catalog/item_list.html', {
        'items':    page,
        'page_obj': page,
        'q':        q,
        'type_id':  type_id,
        'brand_id': brand_id,
        'status':   status,
        'sort':     sort,
        'types':    ItemType.objects.filter(is_active=True),
        'brands':   Brand.objects.filter(is_active=True),
        'has_filter': any([q, type_id, brand_id, status]),
    })


@require_perm(lambda u: u.can_add_item)
def item_create(request):
    form = ItemForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        with transaction.atomic():
            seq, _ = SequenceSetting.objects.select_for_update().get_or_create(key='item', defaults={'next_number': 1})
            if not item.code:
                item.code = seq.next_number
            if item.code >= seq.next_number:
                seq.next_number = item.code + 1
                seq.save(update_fields=['next_number'])
            item.save()
        messages.success(request, 'تم إضافة الصنف.')
        return redirect('catalog:item_list')
    return render(request, 'catalog/item_form.html', {
        'form': form, 'title': 'إضافة صنف جديد',
    })


@require_perm(lambda u: u.can_add_item)
def item_edit(request, pk):
    item = get_object_or_404(Item, pk=pk)
    form = ItemForm(request.POST or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'تم تحديث الصنف.')
        return redirect('catalog:item_list')
    return render(request, 'catalog/item_form.html', {
        'form': form, 'title': f'تعديل: {item.name}', 'item': item,
    })


@require_perm(lambda u: u.can_add_item)
def item_delete(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method != 'POST':
        return redirect('catalog:item_list')

    if item.movements.exists():
        item.is_active = False
        item.save(update_fields=['is_active'])
        messages.warning(request,
            f'الصنف "{item.name}" له حركات — تم إخفاؤه بدل حذفه للحفاظ على التاريخ.')
    else:
        name = item.name
        item.delete()
        messages.success(request, f'تم حذف "{name}".')
    return redirect('catalog:item_list')