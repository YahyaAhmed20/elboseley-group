from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from catalog.models import Item
from inventory.models import StockMovement


@login_required
def index(request):
    q        = request.GET.get('q', '').strip()
    page_num = request.GET.get('page', 1)

    items = list(
        Item.objects
        .filter(is_active=True)
        .select_related('brand', 'type', 'unit')
        .with_balance()
    )

    for i in items:
        if i.min_qty > 0:
            i.fill_pct = min(100, int(float(i.balance / i.min_qty) * 100))
        else:
            i.fill_pct = 100
        i.critical = i.balance <= 0

    total_value = sum(i.value for i in items)

    all_alerts = [i for i in items if i.balance <= i.min_qty]
    all_alerts.sort(key=lambda x: (not x.critical, x.fill_pct))
    total_alerts_count = len(all_alerts)

    if q:
        ql = q.lower()
        all_alerts = [
            a for a in all_alerts
            if ql in a.name.lower()
            or (a.brand and ql in a.brand.name.lower())
            or (a.type and ql in a.type.name.lower())
        ]

    paginator = Paginator(all_alerts, 10)
    alerts_page = paginator.get_page(page_num)

    return render(request, 'dashboard/index.html', {
        'total_items':  len(items),
        'total_alerts': total_alerts_count,
        'total_value':  total_value,
        'total_moves':  StockMovement.objects.count(),
        'alerts':       alerts_page,
        'page_obj':     alerts_page,
        'q':            q,
        'has_filter':   bool(q),
        'filtered_count': len(all_alerts),
    })


@login_required
def reports(request):
    from django.db.models import Q, Sum
    from customers.models import Customer
    from payroll.models import Employee
    from supplier.models import Supplier
    from expenses.models import Expense
    from servicecenter.models import RepairOrder
    from finance.models import FinancialTransaction

    q = request.GET.get('q', '').strip()
    employee_id = request.GET.get('employee', '').strip()
    customer_id = request.GET.get('customer', '').strip()
    supplier_id = request.GET.get('supplier', '').strip()

    delivered = RepairOrder.objects.filter(status=RepairOrder.Status.DELIVERED)
    if q:
        report_q = Q(device__customer__name__icontains=q) | Q(device__customer__phone__icontains=q) | Q(employee__name__icontains=q)
        if q.isdigit(): report_q |= Q(device__code=int(q))
        delivered = delivered.filter(report_q)
    if employee_id: delivered = delivered.filter(employee_id=employee_id)
    if customer_id: delivered = delivered.filter(device__customer_id=customer_id)

    repair_revenue = sum(
        (o.total for o in delivered),
        Decimal('0')
    )

    repair_cost = delivered.aggregate(
        v=Sum('cost')
    )['v'] or Decimal('0')

    repair_profit = repair_revenue - repair_cost

    deposits = delivered.aggregate(
        v=Sum('deposit')
    )['v'] or Decimal('0')

    # إجمالي المقبوض فعليًا من Finance
    collected = FinancialTransaction.objects.filter(
        transaction_type=FinancialTransaction.Type.INCOME,
        repair_order__in=delivered
    ).aggregate(
        v=Sum('amount')
    )['v'] or Decimal('0')

    expenses = Expense.objects.all()
    if employee_id: expenses = expenses.filter(beneficiary_id=employee_id)
    if q: expenses = expenses.filter(Q(beneficiary__name__icontains=q)|Q(category__name__icontains=q)|Q(note__icontains=q))
    total_expenses = expenses.aggregate(v=Sum('amount'))['v'] or Decimal('0')
    net_profit = repair_profit - total_expenses

    supplier_qs = Supplier.objects.filter(is_active=True)
    if supplier_id: supplier_qs = supplier_qs.filter(id=supplier_id)
    supplier_balance = supplier_qs.aggregate(v=Sum('opening_balance'))['v'] or Decimal('0')
    employees = Employee.objects.filter(status=Employee.Status.ACTIVE)
    customers = Customer.objects.all().order_by('name')
    return render(request, 'dashboard/reports.html', {
        'repair_count': delivered.count(),
        'repair_revenue': repair_revenue,
        'collected': collected,
        'repair_cost': repair_cost,
        'repair_profit': repair_profit,
        'deposits': deposits,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'expenses': expenses.select_related('beneficiary', 'category')[:20],
        'delivered': delivered[:20],
        'employees': employees,
        'customers': customers,
        'suppliers': supplier_qs,
        'supplier_balance': supplier_balance,
        'q': q,
        'employee_id': employee_id,
        'customer_id': customer_id,
        'supplier_id': supplier_id,
    })