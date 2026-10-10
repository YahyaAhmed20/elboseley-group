from calendar import monthrange
from datetime import date
from django.db import transaction
from .models import Employee, EmployeePayroll, PayrollMonth, PayrollTransaction


def get_or_create_payroll_month(year, month):
    payroll_month, _ = PayrollMonth.objects.get_or_create(year=year, month=month)
    return payroll_month


@transaction.atomic
def sync_month_employee_payrolls(payroll_month):
    """Create missing monthly salary snapshots for active employees only."""
    active_employees = Employee.objects.filter(status=Employee.Status.ACTIVE)
    existing_ids = set(
        EmployeePayroll.objects.filter(payroll_month=payroll_month)
        .values_list('employee_id', flat=True)
    )
    EmployeePayroll.objects.bulk_create([
        EmployeePayroll(employee=employee, payroll_month=payroll_month, salary=employee.salary)
        for employee in active_employees
        if employee.id not in existing_ids
    ])


def create_transaction(*, payroll_month, employee, kind, amount, note, transaction_date, user):
    employee_payroll, _ = EmployeePayroll.objects.get_or_create(
        employee=employee,
        payroll_month=payroll_month,
        defaults={'salary': employee.salary},
    )
    transaction = PayrollTransaction(
        employee_payroll=employee_payroll,
        kind=kind,
        amount=amount,
        note=note,
        transaction_date=transaction_date,
        created_by=user,
    )
    transaction.full_clean()
    transaction.save()
    return transaction
