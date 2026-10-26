from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from finance.models import (
    Account,
    CashboxTransaction,
    JournalEntry,
    JournalLine,
)
from finance.services import ensure_default_accounts
from payroll.models import Employee
from .forms import ExpenseForm
from .models import Expense, ExpenseCategory
from .services import cancel_expense, create_expense


class ExpenseAccountingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(
            username="expense_test_user",
            password="test-password",
        )

    def setUp(self):
        self.accounts = ensure_default_accounts()

        self.expense_account = Account.objects.create(
            code="5100",
            name="Test Electricity Expense",
            account_type=Account.AccountType.EXPENSE,
        )

        self.category = ExpenseCategory.objects.create(
            name="Test Electricity",
            account=self.expense_account,
        )

        self.employee = Employee.objects.create(
            name="Test Employee",
            salary=Decimal("5000.00"),
        )

        CashboxTransaction.objects.create(
            kind=CashboxTransaction.Kind.OPENING,
            amount=Decimal("5000.00"),
            description="Test opening balance",
            created_by=self.user,
        )

    def _create_expense(self, amount="1000.00"):
        form = ExpenseForm(data={
            "beneficiary": self.employee.pk,
            "category": self.category.pk,
            "amount": amount,
            "expense_date": timezone.localdate().isoformat(),
            "note": "Automated accounting test",
        })
        self.assertTrue(form.is_valid(), form.errors)
        return create_expense(form=form, user=self.user)

    def test_creates_expense_cashbox_transaction_and_balanced_journal(self):
        expense = self._create_expense()

        self.assertEqual(expense.amount, Decimal("1000.00"))

        cashbox_transactions = CashboxTransaction.objects.filter(
            expense=expense,
        )
        self.assertEqual(cashbox_transactions.count(), 1)
        self.assertEqual(
            cashbox_transactions.get().kind,
            CashboxTransaction.Kind.EXPENSE,
        )

        entry = JournalEntry.objects.get(
            reference_type="expense",
            reference_id=expense.pk,
        )
        self.assertEqual(entry.status, JournalEntry.Status.POSTED)

        lines = list(entry.lines.all())
        self.assertEqual(len(lines), 2)
        self.assertEqual(
            sum((line.debit for line in lines), Decimal("0.00")),
            Decimal("1000.00"),
        )
        self.assertEqual(
            sum((line.credit for line in lines), Decimal("0.00")),
            Decimal("1000.00"),
        )

    def test_insufficient_cashbox_balance_rolls_back_expense(self):
        with self.assertRaises(ValidationError):
            self._create_expense("6000.00")

        self.assertEqual(Expense.objects.count(), 0)
        self.assertEqual(
            CashboxTransaction.objects.filter(
                kind=CashboxTransaction.Kind.EXPENSE,
            ).count(),
            0,
        )
        self.assertEqual(
            JournalEntry.objects.filter(
                reference_type="expense",
            ).count(),
            0,
        )

    def test_category_without_account_is_rejected(self):
        self.category.account = None
        self.category.save(update_fields=["account"])

        with self.assertRaises(ValidationError):
            self._create_expense()

        self.assertEqual(Expense.objects.count(), 0)

    def test_cancel_expense_reverses_journal_and_cashbox(self):
        expense = self._create_expense("1000.00")

        original_entry = JournalEntry.objects.get(
            entry_number=f"EXP-{expense.pk}"
        )
        original_cashbox = CashboxTransaction.objects.get(expense=expense)
        balance_before_cancel = (
            Decimal("5000.00") - Decimal("1000.00")
        )

        cancel_expense(expense_id=expense.pk, user=self.user)

        expense.refresh_from_db()
        original_entry.refresh_from_db()

        self.assertTrue(expense.is_cancelled)
        self.assertIsNotNone(expense.cancelled_at)
        self.assertEqual(original_entry.status, JournalEntry.Status.REVERSED)

        reversal_entry = JournalEntry.objects.get(
            entry_number=f"EXR-{expense.pk}"
        )
        self.assertEqual(reversal_entry.status, JournalEntry.Status.POSTED)

        reversal_cashbox = CashboxTransaction.objects.get(
            reverses=original_cashbox
        )
        self.assertEqual(
            reversal_cashbox.kind,
            CashboxTransaction.Kind.INCOME,
        )
        self.assertEqual(reversal_cashbox.amount, Decimal("1000.00"))

        from finance.services import get_cashbox_balance
        self.assertEqual(get_cashbox_balance(), balance_before_cancel + Decimal("1000.00"))

    def test_cannot_cancel_expense_twice(self):
        expense = self._create_expense("1000.00")

        cancel_expense(expense_id=expense.pk, user=self.user)

        with self.assertRaises(ValidationError):
            cancel_expense(expense_id=expense.pk, user=self.user)

        self.assertEqual(
            JournalEntry.objects.filter(
                entry_number=f"EXR-{expense.pk}"
            ).count(),
            1,
        )
        
        
    
    

from django.urls import reverse
from django.contrib.auth import get_user_model


class ExpenseViewTests(ExpenseAccountingTests):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        User = get_user_model()
        cls.admin = User.objects.create_user(
            username="expense_admin",
            password="test-password",
            role=User.Role.ADMIN,
        )
        cls.viewer = User.objects.create_user(
            username="expense_viewer",
            password="test-password",
            role=User.Role.VIEWER,
        )

    def test_get_delete_url_does_not_cancel_expense(self):
        expense = self._create_expense("1000.00")
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("expenses:expense_delete", args=[expense.pk])
        )

        self.assertEqual(response.status_code, 302)
        expense.refresh_from_db()
        self.assertFalse(expense.is_cancelled)

    def test_admin_post_cancels_expense(self):
        expense = self._create_expense("1000.00")
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("expenses:expense_delete", args=[expense.pk])
        )

        self.assertEqual(response.status_code, 302)
        expense.refresh_from_db()
        self.assertTrue(expense.is_cancelled)
        self.assertTrue(
            JournalEntry.objects.filter(
                entry_number=f"EXR-{expense.pk}",
                status=JournalEntry.Status.POSTED,
            ).exists()
        )

    def test_viewer_cannot_cancel_expense(self):
        expense = self._create_expense("1000.00")
        self.client.force_login(self.viewer)

        response = self.client.post(
            reverse("expenses:expense_delete", args=[expense.pk])
        )

        self.assertEqual(response.status_code, 403)
        expense.refresh_from_db()
        self.assertFalse(expense.is_cancelled)

    def test_expense_list_total_excludes_cancelled_expenses(self):
        active_expense = self._create_expense("1000.00")
        cancelled_expense = self._create_expense("500.00")
        cancel_expense(
            expense_id=cancelled_expense.pk,
            user=self.user,
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse("expenses:expense_list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total"], Decimal("1000.00"))
