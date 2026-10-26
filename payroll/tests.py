from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from .models import Employee, EmployeePayroll, PayrollMonth, PayrollTransaction
from .services import create_transaction, sync_month_employee_payrolls


class PayrollTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='admin', password='pass', role='admin')
        self.employee = Employee.objects.create(name='محمد', salary=Decimal('8000'))

    def test_month_keeps_salary_snapshot(self):
        september = PayrollMonth.objects.create(year=2026, month=9)
        sync_month_employee_payrolls(september)
        self.employee.salary = Decimal('9000')
        self.employee.save(update_fields=['salary', 'updated_at'])
        october = PayrollMonth.objects.create(year=2026, month=10)
        sync_month_employee_payrolls(october)

        self.assertEqual(EmployeePayroll.objects.get(employee=self.employee, payroll_month=september).salary, Decimal('8000'))
        self.assertEqual(EmployeePayroll.objects.get(employee=self.employee, payroll_month=october).salary, Decimal('9000'))

    def test_transactions_are_isolated_by_month(self):
        september = PayrollMonth.objects.create(year=2026, month=9)
        october = PayrollMonth.objects.create(year=2026, month=10)
        sync_month_employee_payrolls(september)
        sync_month_employee_payrolls(october)
        create_transaction(
            payroll_month=september, employee=self.employee,
            kind=PayrollTransaction.Kind.ADVANCE, amount=Decimal('1000'),
            note='سلفة', transaction_date=date(2026, 9, 10), user=self.user,
        )
        self.assertEqual(
            EmployeePayroll.objects.get(employee=self.employee, payroll_month=september).total_deductions,
            Decimal('1000'),
        )
        self.assertEqual(
            EmployeePayroll.objects.get(employee=self.employee, payroll_month=october).total_deductions,
            Decimal('0'),
        )

    def test_transaction_cannot_use_wrong_month_date(self):
        september = PayrollMonth.objects.create(year=2026, month=9)
        with self.assertRaises(ValidationError):
            create_transaction(
                payroll_month=september, employee=self.employee,
                kind=PayrollTransaction.Kind.WASTE, amount=Decimal('100'),
                note='هدر', transaction_date=date(2026, 10, 1), user=self.user,
            )