from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render


from decimal import Decimal
from purchases.models import SupplierAccountEntry
from decimal import Decimal
from django.db.models import Sum

from accounts.decorators import require_perm
from .forms import SupplierForm
from .models import Supplier


@require_perm(lambda u: u.can_manage_operations)
def supplier_list(request):
    q = request.GET.get('q', '').strip()

    suppliers = Supplier.objects.filter(is_active=True)

    if q:
        suppliers = suppliers.filter(
            Q(code__icontains=q) |
            Q(name__icontains=q) |
            Q(phone__icontains=q)
        )

    suppliers = suppliers.annotate(
        total_purchases=Sum('account_entries__credit'),
        total_paid=Sum('account_entries__debit'),
    )

    page = Paginator(suppliers, 20).get_page(
        request.GET.get('page')
    )

    for supplier in page:
        supplier.total_purchases = (
            supplier.total_purchases or Decimal('0.00')
        )
        supplier.total_paid = (
            supplier.total_paid or Decimal('0.00')
        )

        supplier.current_balance = (
            supplier.opening_balance
            + supplier.total_purchases
            - supplier.total_paid
        )

    return render(request, 'supplier/supplier_list.html', {
        'suppliers': page,
        'page_obj': page,
        'q': q,
    })


@require_perm(lambda u: u.can_manage_operations)
def supplier_create(request):
    form = SupplierForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'تم إضافة المورد.')
        return redirect('supplier:supplier_list')
    return render(request, 'supplier/supplier_form.html', {
        'form': form,
        'title': 'إضافة مورد',
    })


@require_perm(lambda u: u.can_manage_operations)
def supplier_edit(request, pk):
    obj = get_object_or_404(Supplier, pk=pk)
    form = SupplierForm(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'تم تحديث المورد.')
        return redirect('supplier:supplier_list')
    return render(request, 'supplier/supplier_form.html', {
        'form': form,
        'title': f'تعديل: {obj.name}',
    })


@require_perm(lambda u: u.can_manage_operations)
def supplier_delete(request, pk):
    obj = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        messages.success(request, 'تم إخفاء المورد.')
    return redirect('supplier:supplier_list')



@require_perm(lambda u: u.can_manage_operations)
def supplier_statement(request, pk):
    supplier = get_object_or_404(
        Supplier,
        pk=pk,
        is_active=True,
    )

    entries = list(
        SupplierAccountEntry.objects
        .filter(supplier=supplier)
        .select_related("invoice", "created_by")
        .order_by("created_at", "id")
    )

    balance = supplier.opening_balance
    total_purchases = Decimal("0.00")
    total_paid = Decimal("0.00")
    rows = []

    for entry in entries:
        total_purchases += entry.credit
        total_paid += entry.debit

        balance += entry.credit - entry.debit

        rows.append({
            "entry": entry,
            "balance": balance,
        })

    return render(
        request,
        "supplier/supplier_statement.html",
        {
            "supplier": supplier,
            "rows": rows,
            "total_purchases": total_purchases,
            "total_paid": total_paid,
            "current_balance": balance,
        },
    )
