from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from finance.models import Account, CashboxTransaction, JournalEntry
from finance.services import (
    create_journal_entry,
    ensure_default_accounts,
    reverse_journal_entry,
    validate_cashbox_expense,
)
from .models import Expense


@transaction.atomic
def create_expense(*, form, user):
    if not user or not user.is_authenticated:
        raise ValidationError("يجب تسجيل الدخول لتسجيل المصروف.")

    expense = form.save(commit=False)

    amount = Decimal(str(expense.amount))
    if not amount.is_finite() or amount <= 0:
        raise ValidationError("قيمة المصروف يجب أن تكون أكبر من صفر.")

    category = expense.category
    account = category.account

    if not account or not account.is_active:
        raise ValidationError(
            "يجب ربط بند المصروف بحساب محاسبي نشط أولاً."
        )

    if account.account_type != Account.AccountType.EXPENSE:
        raise ValidationError(
            "الحساب المرتبط ببند المصروف يجب أن يكون حساب مصروفات."
        )

    validate_cashbox_expense(amount)
    accounts = ensure_default_accounts()

    expense.created_by = user
    expense.save()

    cashbox_transaction = CashboxTransaction.objects.create(
        kind=CashboxTransaction.Kind.EXPENSE,
        amount=amount,
        description=f"مصروف #{expense.pk}: {category.name}",
        created_by=user,
        expense=expense,
    )

    create_journal_entry(
        entry_number=f"EXP-{expense.pk}",
        entry_date=expense.expense_date or timezone.localdate(),
        description=f"مصروف: {category.name} - {expense.pk}",
        reference_type="expense",
        reference_id=expense.pk,
        user=user,
        lines=[
            {
                "account_id": account.pk,
                "debit": amount,
                "credit": Decimal("0.00"),
                "description": category.name,
            },
            {
                "account_id": accounts["1000"].pk,
                "debit": Decimal("0.00"),
                "credit": amount,
                "description": "صرف من الخزنة",
            },
        ],
    )

    return expense


@transaction.atomic
def cancel_expense(*, expense_id, user):
    if not user or not user.is_authenticated:
        raise ValidationError("يجب تسجيل الدخول لإلغاء المصروف.")

    expense = Expense.objects.select_for_update().select_related(
        "category"
    ).get(pk=expense_id)

    if expense.is_cancelled:
        raise ValidationError("هذا المصروف ملغي بالفعل.")

    cashbox_transaction = CashboxTransaction.objects.select_for_update().filter(
        expense=expense,
        is_reversal=False,
    ).first()

    if cashbox_transaction is None:
        raise ValidationError("لا توجد حركة خزنة أصلية مرتبطة بهذا المصروف.")

    if hasattr(cashbox_transaction, "reversal_transaction"):
        raise ValidationError("حركة الخزنة لهذا المصروف معكوسة بالفعل.")

    original_entry = JournalEntry.objects.filter(
        entry_number=f"EXP-{expense.pk}",
        reference_type="expense",
        reference_id=expense.pk,
    ).first()

    if original_entry is None:
        raise ValidationError("لا يوجد قيد محاسبي أصلي لهذا المصروف.")

    reversal = reverse_journal_entry(
        entry_id=original_entry.pk,
        user=user,
        reversal_number=f"EXR-{expense.pk}",
        reversal_date=timezone.localdate(),
    )

    CashboxTransaction.objects.create(
        kind=CashboxTransaction.Kind.INCOME,
        amount=cashbox_transaction.amount,
        description=f"عكس مصروف #{expense.pk}",
        created_by=user,
        is_reversal=True,
        reverses=cashbox_transaction,
    )

    expense.is_cancelled = True
    expense.cancelled_at = timezone.now()
    expense.save(update_fields=["is_cancelled", "cancelled_at"])

    return expense