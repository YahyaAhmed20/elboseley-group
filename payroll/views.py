from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import ValidationError
from django.utils import timezone
from accounts.decorators import require_perm
from .forms import EmployeeForm, PayrollTransactionForm
from .models import Employee, EmployeePayroll, PayrollMonth, PayrollTransaction
from .services import create_transaction, get_or_create_payroll_month, sync_month_employee_payrolls


def _selected_month(request):
    today = timezone.localdate()
    raw = request.GET.get('month', '').strip()
    if raw:
        try:
            year, month = map(int, raw.split('-'))
            if 1 <= month <= 12 and 2000 <= year <= 2100:
                return get_or_create_payroll_month(year, month)
        except (TypeError, ValueError):
            pass
    return get_or_create_payroll_month(today.year, today.month)


@require_perm(lambda u: u.can_manage_employees)
def employee_list(request):
    payroll_month = _selected_month(request)
    sync_month_employee_payrolls(payroll_month)

    q = request.GET.get('q', '').strip()
    payrolls = (EmployeePayroll.objects.filter(payroll_month=payroll_month)
        .select_related('employee')
        .annotate(
            advance_total=Sum('transactions__amount', filter=Q(transactions__kind=PayrollTransaction.Kind.ADVANCE)),
            waste_total=Sum('transactions__amount', filter=Q(transactions__kind=PayrollTransaction.Kind.WASTE)),
            other_total=Sum('transactions__amount', filter=Q(transactions__kind=PayrollTransaction.Kind.OTHER)),
        ))
    if q:
        payrolls = payrolls.filter(Q(employee__name__icontains=q) | Q(employee__notes__icontains=q))
    rows = []
    for p in payrolls:
        advance = p.advance_total or 0
        waste = p.waste_total or 0
        other = p.other_total or 0
        rows.append({
            'employee': p.employee,
            'payroll': p,
            'net_salary': p.salary - advance - waste - other,
        })

    return render(request, 'payroll/employee_list.html', {
        'rows': rows,
        'payroll_month': payroll_month,
        'months': PayrollMonth.objects.all(),
        'q': q,
    })


@require_perm(lambda u: u.can_manage_employees)
def employee_create(request):
    form = EmployeeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'تم إضافة العامل.')
        return redirect('payroll:employee_list')
    return render(request, 'payroll/employee_form.html', {'form': form, 'title': 'إضافة عامل'})


@require_perm(lambda u: u.can_manage_employees)
def employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    form = EmployeeForm(request.POST or None, instance=employee)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'تم تحديث بيانات العامل. المرتبات السابقة لن تتغير.')
        return redirect('payroll:employee_list')
    return render(request, 'payroll/employee_form.html', {'form': form, 'title': f'تعديل: {employee.name}'})


@require_perm(lambda u: u.can_manage_employees)
def transaction_list(request):
    payroll_month = _selected_month(request)
    sync_month_employee_payrolls(payroll_month)
    employee_id = request.GET.get('employee', '').strip()
    kind = request.GET.get('kind', '').strip()
    q = request.GET.get('q', '').strip()

    transactions = PayrollTransaction.objects.filter(
        employee_payroll__payroll_month=payroll_month
    ).select_related('employee_payroll__employee', 'created_by')
    if employee_id:
        transactions = transactions.filter(employee_payroll__employee_id=employee_id)
    if kind in dict(PayrollTransaction.Kind.choices):
        transactions = transactions.filter(kind=kind)
    if q:
        transactions = transactions.filter(
            Q(employee_payroll__employee__name__icontains=q) | Q(note__icontains=q)
        )

    paginator = Paginator(transactions, 20)
    page = paginator.get_page(request.GET.get('page'))

    month_payrolls = EmployeePayroll.objects.filter(
        payroll_month=payroll_month
    ).select_related('employee')
    employees = Employee.objects.filter(status=Employee.Status.ACTIVE)
    total_advance = transactions.filter(kind=PayrollTransaction.Kind.ADVANCE).aggregate(total=Sum('amount'))['total'] or 0
    total_waste = transactions.filter(kind=PayrollTransaction.Kind.WASTE).aggregate(total=Sum('amount'))['total'] or 0
    total_other = transactions.filter(kind=PayrollTransaction.Kind.OTHER).aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'payroll/transaction_list.html', {
        'transactions': page,
        'page_obj': page,
        'payroll_month': payroll_month,
        'months': PayrollMonth.objects.all(),
        'employees': employees,
        'kind_choices': PayrollTransaction.Kind.choices,
        'month_payrolls': month_payrolls,
        'employee_id': employee_id,
        'kind': kind,
        'q': q,
        'total_advance': total_advance,
        'total_waste': total_waste,
        'total_other': total_other,
    })


@require_perm(lambda u: u.can_manage_employees)
def transaction_create(request):
    payroll_month = _selected_month(request)
    employee_id = request.GET.get('employee', '').strip() or request.POST.get('employee', '').strip()
    employee = Employee.objects.filter(pk=employee_id).first() if employee_id else None

    form = PayrollTransactionForm(
        request.POST or None,
        payroll_month=payroll_month,
        initial={'transaction_date': timezone.localdate() if timezone.localdate().strftime('%Y-%m') == str(payroll_month) else payroll_month.created_at.date().replace(day=1)},
    )
    if request.method == 'POST' and form.is_valid() and employee:
        try:
            create_transaction(
                payroll_month=payroll_month,
                employee=employee,
                kind=form.cleaned_data['kind'],
                amount=form.cleaned_data['amount'],
                note=form.cleaned_data['note'],
                transaction_date=form.cleaned_data['transaction_date'],
                user=request.user,
            )
        except ValidationError as exc:
            for field, errors in exc.message_dict.items():
                for error in errors:
                    form.add_error(field, error)
            return render(request, 'payroll/transaction_form.html', {
                'form': form, 'employee': employee, 'payroll_month': payroll_month,
                'employees': Employee.objects.filter(status=Employee.Status.ACTIVE),
            })
        messages.success(request, 'تم تسجيل الخصم على الشهر المحدد.')
        return redirect(f'/payroll/transactions/?month={payroll_month}&employee={employee.id}')

    if request.method == 'POST' and not employee:
        form.add_error(None, 'اختر العامل أولًا.')

    return render(request, 'payroll/transaction_form.html', {
        'form': form,
        'employee': employee,
        'payroll_month': payroll_month,
        'employees': Employee.objects.filter(status=Employee.Status.ACTIVE),
    })


@require_perm(lambda u: u.can_manage_employees)
def transaction_delete(request, pk):
    transaction = get_object_or_404(
        PayrollTransaction.objects.select_related('employee_payroll__payroll_month'), pk=pk
    )
    if request.method == 'POST':
        month = transaction.employee_payroll.payroll_month
        transaction.delete()
        messages.success(request, 'تم حذف العملية.')
        return redirect(f'/payroll/transactions/?month={month}')
    return redirect('payroll:transaction_list')
