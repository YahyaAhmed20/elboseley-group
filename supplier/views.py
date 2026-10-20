from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

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
    page = Paginator(suppliers, 20).get_page(request.GET.get('page'))
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