from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import require_perm
from .forms import CustomerForm
from .models import Customer
from .services import build_reminder_message, send_telegram_message, telegram_configured


@require_perm(lambda u: u.can_manage_customers)
def customer_list(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    customers = Customer.objects.all().select_related('created_by')
    if q:
        customers = customers.filter(
            Q(code__icontains=q) |
            Q(name__icontains=q) |
            Q(phone__icontains=q) |
            Q(personal_number__icontains=q) |
            Q(car_number__icontains=q) |
            Q(note__icontains=q)
        )
    if status == 'reminder':
        customers = customers.filter(follow_up_enabled=True)
    elif status == 'due':
        customers = customers.filter(follow_up_enabled=True, follow_up_date__lte=timezone.localdate(), reminder_sent_at__isnull=True)

    paginator = Paginator(customers, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'customers/customer_list.html', {
        'customers': page,
        'page_obj': page,
        'q': q,
        'status': status,
        'telegram_configured': telegram_configured(),
        'today': timezone.localdate(),
    })


@require_perm(lambda u: u.can_manage_customers)
def customer_create(request):
    form = CustomerForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        customer = form.save(commit=False)
        customer.created_by = request.user
        customer.save()

        if customer.follow_up_enabled:
            customer.set_follow_up(True)
            customer.save(update_fields=[
                'follow_up_enabled',
                'follow_up_date',
                'reminder_sent_at',
                'updated_at',
            ])

        messages.success(
            request,
            'تم إضافة العميل وحفظ موعد المراجعة.'
            if customer.follow_up_enabled
            else 'تم إضافة العميل.'
        )

        next_url = request.GET.get('next') or request.POST.get('next')

        if next_url == 'repair_receive':
            from django.urls import reverse
            from urllib.parse import urlencode
            url = reverse('servicecenter:repair_receive')
            return redirect(f'{url}?{urlencode({"customer": customer.pk})}')

        return redirect('customers:customer_list')

    return render(request, 'customers/customer_form.html', {
        'form': form,
        'title': 'إضافة عميل',
        'next': request.GET.get('next', ''),
    })


@require_perm(lambda u: u.can_manage_customers)
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == 'POST' and form.is_valid():
        enabled = form.cleaned_data['follow_up_enabled']
        was_enabled = customer.follow_up_enabled
        customer = form.save(commit=False)
        if enabled and not was_enabled:
            customer.set_follow_up(True)
        elif not enabled:
            customer.set_follow_up(False)
        else:
            customer.follow_up_enabled = True
        customer.save()
        messages.success(request, 'تم تحديث بيانات العميل.')
        return redirect('customers:customer_list')
    return render(request, 'customers/customer_form.html', {'form': form, 'title': f'تعديل: {customer.name}', 'customer': customer})


@require_perm(lambda u: u.can_manage_customers)
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        customer.delete()
        messages.success(request, 'تم حذف العميل.')
    return redirect('customers:customer_list')


@require_perm(lambda u: u.can_manage_customers)
def customer_pdf(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    try:
        from .pdf import customer_pdf_response
    except ImportError:
        return HttpResponse('مكتبة PDF غير مثبتة. شغّل: pip install -r requirements.txt', status=500)
    return customer_pdf_response(customer)


@require_perm(lambda u: u.can_manage_customers)
def customer_telegram_test(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        try:
            send_telegram_message(build_reminder_message(customer))
            messages.success(request, 'تم إرسال التذكير إلى Telegram.')
        except Exception as exc:
            messages.error(request, f'فشل إرسال Telegram: {exc}')
    return redirect('customers:customer_list')