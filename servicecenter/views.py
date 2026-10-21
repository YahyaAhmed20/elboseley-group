
from django.http import JsonResponse
from django.db.models import Q
from decimal import Decimal
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum, F, Value, DecimalField, ExpressionWrapper
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from accounts.decorators import require_perm
from .forms import RepairReceiveForm, RepairWorkForm, RepairFilterForm
from .models import Device, RepairOrder, SequenceSetting
from customers.models import Customer
from finance.models import FinancialTransaction
import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET
from django.conf import settings
from pathlib import Path


def _next_code(key):
    with transaction.atomic():
        seq, _ = SequenceSetting.objects.select_for_update().get_or_create(key=key, defaults={'next_number':1})
        code=seq.next_number; seq.next_number += 1; seq.save(update_fields=['next_number']); return code

@require_perm(lambda u: u.can_manage_operations)
def repair_list(request):
    form = RepairFilterForm(request.GET or None)

    qs = RepairOrder.objects.select_related(
        'device__customer',
        'employee'
    )

    if form.is_valid():
        q = form.cleaned_data.get('q')
        status = form.cleaned_data.get('status')
        employee = form.cleaned_data.get('employee')

        if q:
            q = q.strip()
            search_q = Q(
                device__customer__name__icontains=q
            ) | Q(
                device__customer__phone__icontains=q
            ) | Q(
                device__device_type__icontains=q
            ) | Q(
                device__description__icontains=q
            ) | Q(
                fault_description__icontains=q
            ) | Q(
                repair_notes__icontains=q
            ) | Q(
                employee__name__icontains=q
            ) | Q(
                deposit__icontains=q
            ) | Q(
                cost__icontains=q
            ) | Q(
                labor__icontains=q
            )

            # البحث بالكود: 2 أو #2
            code_value = q.lstrip('#').strip()

            if code_value.isdigit():
                search_q |= Q(
                    device__code=int(code_value)
                )

            # البحث في الإجمالي = التكلفة + المصنعية
            try:
                total_value = Decimal(
                    code_value.replace(',', '')
                )

                qs = qs.annotate(
                    calculated_total=ExpressionWrapper(
                        F('cost') + F('labor'),
                        output_field=DecimalField(
                            max_digits=12,
                            decimal_places=2
                        )
                    )
                )

                search_q |= Q(
                    calculated_total=total_value
                )

            except Exception:
                pass

            # البحث بالحالة
            for value, label in RepairOrder.Status.choices:
                if q == value or q in label or label in q:
                    search_q |= Q(status=value)

            qs = qs.filter(search_q)

        if status:
            qs = qs.filter(status=status)

        if employee:
            qs = qs.filter(employee=employee)

    page = Paginator(qs, 20).get_page(
        request.GET.get('page')
    )

    return render(
        request,
        'servicecenter/repair_list.html',
        {
            'orders': page,
            'page_obj': page,
            'form': form
        }
    )
    
    
    
@require_perm(lambda u: u.can_manage_operations)
def customer_search(request):
    if not request.user.is_authenticated:
        return JsonResponse([], safe=False, status=401)

    q = request.GET.get('q', '').strip()

    if len(q) < 2:
        return JsonResponse([], safe=False)

    customers = Customer.objects.filter(
        Q(name__istartswith=q) |
        Q(phone__istartswith=q)
    ).order_by('name')[:10]

    results = [
        {
            'id': customer.pk,
            'name': customer.name,
            'phone': customer.phone or '',
            'label': f'{customer.name} - {customer.phone or "بدون هاتف"}',
        }
        for customer in customers
    ]

    return JsonResponse(results, safe=False)


@require_perm(lambda u: u.can_manage_operations)
def device_search(request):
    if not request.user.is_authenticated:
        return JsonResponse([], safe=False, status=401)

    q = request.GET.get('q', '').strip()
    customer_id = request.GET.get('customer_id', '').strip()

    if len(q) < 1 or not customer_id:
        return JsonResponse([], safe=False)

    devices = Device.objects.select_related('customer').filter(
        customer_id=customer_id
    )

    search_filter = (
        Q(customer__name__icontains=q)
        | Q(customer__phone__icontains=q)
        | Q(device_type__icontains=q)
        | Q(description__icontains=q)
    )

    if q.isdigit():
        search_filter |= Q(code=int(q))

    devices = devices.filter(search_filter).order_by('-created_at')[:10]

    results = [
        {
            'id': device.pk,
            'code': device.code,
            'device_type': device.device_type,
            'customer': device.customer.name,
            'phone': device.customer.phone or '',
            'label': (
                f'#{device.code} - {device.device_type} - '
                f'{device.customer.name} - {device.customer.phone or "بدون هاتف"}'
            ),
        }
        for device in devices
    ]

    return JsonResponse(results, safe=False)



@require_perm(lambda u: u.can_manage_operations)
def repair_receive(request):
    initial = {}
    customer_id = request.GET.get('customer')

    if customer_id and request.method == 'GET':
        initial['customer_id'] = customer_id

    form = RepairReceiveForm(
        request.POST or None,
        initial=initial,
    )

    if request.method == 'POST' and form.is_valid():
        customer = form.cleaned_data['customer']
        existing = form.cleaned_data['existing_device']
        deposit = form.cleaned_data['deposit']

        with transaction.atomic():
            if existing:
                device = existing
            else:
                code = _next_code('device')
                device = Device.objects.create(
                    code=code,
                    customer=customer,
                    device_type=form.cleaned_data['device_type'],
                    description=form.cleaned_data['device_description'],
                )

            order = RepairOrder.objects.create(
                device=device,
                received_at=timezone.now(),
                fault_description=form.cleaned_data['fault_description'],
                deposit=deposit,
                created_by=request.user,
            )

            if deposit > 0:
                FinancialTransaction.objects.create(
                    transaction_type=FinancialTransaction.Type.INCOME,
                    amount=deposit,
                    description=f'عربون صيانة #{order.pk}',
                    repair_order=order,
                    created_by=request.user,
                )

        messages.success(
            request,
            f'تم استلام الجهاز بكود {device.code}.',
        )

        return redirect(
            'servicecenter:repair_receipt',
            pk=order.pk,
        )

    return render(
        request,
        'servicecenter/repair_receive.html',
        {
            'form': form,
            'title': 'إيصال استلام جهاز',
        },
    )

@require_perm(lambda u: u.can_manage_operations)
def repair_work(request,pk):
    order=get_object_or_404(RepairOrder.objects.select_related('device__customer'),pk=pk)
    form=RepairWorkForm(request.POST or None,instance=order)
    if request.method=='POST' and form.is_valid():
        order=form.save(commit=False)
        if not order.repair_date: order.repair_date=timezone.now()
        if order.status == RepairOrder.Status.DELIVERED:
            order.delivered_at=timezone.now()
        order.save()
        messages.success(request,'تم تحديث أمر الصيانة.')
        return redirect('servicecenter:repair_list')
    return render(request,'servicecenter/repair_work.html',{'form':form,'order':order})

@require_perm(lambda u: u.can_manage_operations)
def repair_deliver(request, pk):
    order = get_object_or_404(
        RepairOrder.objects.select_related('device__customer'),
        pk=pk
    )

    if request.method == 'POST':

        if order.status == RepairOrder.Status.DELIVERED:
            messages.warning(request, 'هذا الجهاز تم تسليمه بالفعل.')
            return redirect('servicecenter:repair_list')

        # لا يمكن التسليم قبل تحديد تكلفة الإصلاح
        if order.total <= 0:
            messages.error(
                request,
                'لا يمكن تسليم الجهاز قبل تحديد التكلفة والمصنعية.'
            )
            return redirect('servicecenter:repair_list')

        # العربون لا يمكن أن يكون أكبر من إجمالي الصيانة
        if order.deposit > order.total:
            messages.error(
                request,
                'العربون أكبر من إجمالي الصيانة، يرجى مراجعة البيانات.'
            )
            return redirect('servicecenter:repair_list')

        # يجب أن يكون أمر الصيانة جاهزًا للتسليم
        if order.status != RepairOrder.Status.READY:
            messages.warning(
                request,
                'يجب تغيير حالة الجهاز إلى "جاهز للتسليم" أولًا.'
            )
            return redirect('servicecenter:repair_list')

        remaining = order.remaining

        with transaction.atomic():

            if remaining > 0:
                FinancialTransaction.objects.create(
                    transaction_type=FinancialTransaction.Type.INCOME,
                    amount=remaining,
                    description=f'تحصيل تسليم صيانة #{order.pk}',
                    repair_order=order,
                    created_by=request.user,
                )

            order.paid_at_delivery = remaining
            order.status = RepairOrder.Status.DELIVERED
            order.delivered_at = timezone.now()

            order.save(update_fields=[
                'paid_at_delivery',
                'status',
                'delivered_at',
            ])

        messages.success(
            request,
            f'تم تسليم الجهاز واستلام {remaining} ج.م.'
        )

    return redirect('servicecenter:repair_list')

@require_perm(lambda u: u.can_manage_operations)
def repair_receipt(request,pk):
    order=get_object_or_404(RepairOrder.objects.select_related('device__customer'),pk=pk)
    return render(request,'servicecenter/repair_receipt.html',{'order':order})

@require_perm(lambda u: u.can_manage_operations)
def device_list(request):
    q=request.GET.get('q','').strip(); qs=Device.objects.select_related('customer')
    if q:
        text_q = Q(customer__name__icontains=q) | Q(customer__phone__icontains=q)
        if q.isdigit(): text_q |= Q(code=int(q))
        qs = qs.filter(text_q)
    page=Paginator(qs,20).get_page(request.GET.get('page'))
    return render(request,'servicecenter/device_list.html',{'devices':page,'page_obj':page,'q':q})

@require_perm(lambda u: u.can_manage_operations)
def device_detail(request, pk):
    device = get_object_or_404(
        Device.objects.select_related('customer'),
        pk=pk
    )

    repairs = device.repairs.select_related(
        'employee'
    ).order_by('-received_at')

    return render(
        request,
        'servicecenter/device_detail.html',
        {
            'device': device,
            'repairs': repairs,
        }
    )
    
    
@require_GET
@require_perm(lambda u: u.can_manage_operations)
def qz_sign(request):
    to_sign = request.GET.get('request')

    if not to_sign:
        return JsonResponse(
            {'error': 'Missing request parameter'},
            status=400
        )

    key_path = Path(settings.BASE_DIR) / 'qz' / 'private-key.pem'

    try:
        private_key = serialization.load_pem_private_key(
            key_path.read_bytes(),
            password=None,
        )

        signature = private_key.sign(
            to_sign.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA512(),
        )

        return HttpResponse(
            base64.b64encode(signature).decode('ascii'),
            content_type='text/plain',
        )

    except Exception as exc:
        return JsonResponse(
            {'error': str(exc)},
            status=500
        )