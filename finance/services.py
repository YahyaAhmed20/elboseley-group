from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, Case, When, F, DecimalField, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import (
    Account,
    JournalEntry,
    JournalLine,
    CashboxTransaction,
)


ZERO = Decimal("0.00")


def get_cashbox_balance():
    """Return the current cashbox balance from recorded transactions."""
    balance = CashboxTransaction.objects.aggregate(
        balance=Coalesce(
            Sum(
                Case(
                    When(
                        kind__in=[
                            CashboxTransaction.Kind.INCOME,
                            CashboxTransaction.Kind.OPENING,
                        ],
                        then=F("amount"),
                    ),
                    When(
                        kind=CashboxTransaction.Kind.EXPENSE,
                        then=-F("amount"),
                    ),
                    default=Value(ZERO),
                    output_field=DecimalField(
                        max_digits=12,
                        decimal_places=2,
                    ),
                )
            ),
            Value(ZERO),
            output_field=DecimalField(
                max_digits=12,
                decimal_places=2,
            ),
        )
    )["balance"]

    return balance or ZERO


def validate_cashbox_expense(amount):
    """Reject invalid or unaffordable cash outflows."""
    try:
        amount = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("أدخل مبلغًا رقميًا صحيحًا.")

    if not amount.is_finite() or amount <= ZERO:
        raise ValidationError("مبلغ الصرف يجب أن يكون أكبر من صفر.")

    balance = get_cashbox_balance()

    if amount > balance:
        raise ValidationError(
            f"رصيد الخزنة غير كافٍ. الرصيد الحالي: {balance:.2f} جنيه."
        )


def _to_money(value):
    """Convert an input to a finite, non-negative Decimal amount."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("قيمة مالية غير صحيحة.")

    if not amount.is_finite() or amount < ZERO:
        raise ValidationError("القيمة المالية يجب أن تكون صفرًا أو أكثر.")

    return amount.quantize(Decimal("0.01"))


def _validate_entry_balance(lines):
    """Require at least two lines and equal positive debit/credit totals."""
    if len(lines) < 2:
        raise ValidationError("القيد المحاسبي يجب أن يحتوي على سطرين على الأقل.")

    debit_total = ZERO
    credit_total = ZERO

    for line in lines:
        debit = _to_money(line.get("debit", ZERO))
        credit = _to_money(line.get("credit", ZERO))

        if (debit > ZERO and credit > ZERO) or (
            debit == ZERO and credit == ZERO
        ):
            raise ValidationError(
                "كل سطر يجب أن يحتوي على مدين أو دائن فقط."
            )

        debit_total += debit
        credit_total += credit

    if debit_total <= ZERO:
        raise ValidationError("إجمالي القيد يجب أن يكون أكبر من صفر.")

    if debit_total != credit_total:
        raise ValidationError(
            f"القيد غير متوازن: المدين {debit_total:.2f} "
            f"والدائن {credit_total:.2f}."
        )


@transaction.atomic
def create_journal_entry(
    *,
    entry_number,
    entry_date,
    description,
    lines,
    user,
    reference_type="",
    reference_id=None,
):
    """
    Create and post a balanced journal entry atomically.

    Each line must contain:
        account_id, debit, credit, and optionally description.

    This function posts the entry immediately. It does not update
    cashbox transactions or operational records automatically.
    """
    if not user or not getattr(user, "is_authenticated", False):
        raise ValidationError("يجب تحديد مستخدم مسجل الدخول.")

    if not entry_number or not str(entry_number).strip():
        raise ValidationError("رقم القيد مطلوب.")

    if not description or not str(description).strip():
        raise ValidationError("بيان القيد مطلوب.")

    if not lines:
        raise ValidationError("أضف سطور القيد المحاسبي.")

    normalized_lines = []
    account_ids = set()

    for line in lines:
        if not isinstance(line, dict):
            raise ValidationError("صيغة سطر القيد غير صحيحة.")

        try:
            account_id = int(line["account_id"])
        except (KeyError, TypeError, ValueError):
            raise ValidationError("كل سطر يجب أن يحتوي على حساب صحيح.")

        debit = _to_money(line.get("debit", ZERO))
        credit = _to_money(line.get("credit", ZERO))

        normalized_lines.append({
            "account_id": account_id,
            "debit": debit,
            "credit": credit,
            "description": str(line.get("description", "")),
        })
        account_ids.add(account_id)

    _validate_entry_balance(normalized_lines)

    accounts = {
        account.pk: account
        for account in Account.objects.select_for_update().filter(
            pk__in=account_ids,
            is_active=True,
        )
    }

    if len(accounts) != len(account_ids):
        raise ValidationError("يوجد حساب غير موجود أو غير نشط.")

    entry = JournalEntry.objects.create(
        entry_number=str(entry_number).strip(),
        entry_date=entry_date,
        description=str(description).strip(),
        reference_type=reference_type,
        reference_id=reference_id,
        status=JournalEntry.Status.DRAFT,
        created_by=user,
    )

    JournalLine.objects.bulk_create([
        JournalLine(
            entry=entry,
            account=accounts[line["account_id"]],
            debit=line["debit"],
            credit=line["credit"],
            description=line["description"],
        )
        for line in normalized_lines
    ])

    entry.status = JournalEntry.Status.POSTED
    entry.posted_at = timezone.now()
    entry.save(update_fields=["status", "posted_at"])

    return entry


@transaction.atomic
def reverse_journal_entry(*, entry_id, user, reversal_number, reversal_date=None):
    """
    Reverse a posted journal entry with a separate, opposite entry.
    The original entry remains unchanged.
    """
    if not user or not getattr(user, "is_authenticated", False):
        raise ValidationError("يجب تحديد مستخدم مسجل الدخول.")

    original = JournalEntry.objects.select_for_update().get(pk=entry_id)

    if original.status != JournalEntry.Status.POSTED:
        raise ValidationError("لا يمكن عكس قيد غير مُرحّل.")

    original_lines = list(
        original.lines.select_related("account").all()
    )

    reversal_lines = [
        {
            "account_id": line.account_id,
            "debit": line.credit,
            "credit": line.debit,
            "description": line.description,
        }
        for line in original_lines
    ]

    reversal = create_journal_entry(
        entry_number=reversal_number,
        entry_date=reversal_date or timezone.localdate(),
        description=f"عكس القيد {original.entry_number}",
        lines=reversal_lines,
        user=user,
        reference_type="journal_reversal",
        reference_id=original.pk,
    )

    original.status = JournalEntry.Status.REVERSED
    original.save(update_fields=["status"])

    return reversal







@transaction.atomic
def ensure_default_accounts():
    """
    Create the minimum system accounts needed by the accounting flows.
    Safe to call repeatedly; existing account codes are preserved.
    """
    defaults = [
        ("1000", "الخزنة", Account.AccountType.ASSET),
        ("1200", "المخزون", Account.AccountType.ASSET),
        ("2000", "الموردون", Account.AccountType.LIABILITY),
        ("4000", "إيرادات الخدمات", Account.AccountType.REVENUE),
        ("5000", "مصروفات التشغيل", Account.AccountType.EXPENSE),
    ]

    accounts = {}

    for code, name, account_type in defaults:
        account, _ = Account.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "account_type": account_type,
                "is_active": True,
                "is_system": True,
            },
        )

        if account.account_type != account_type:
            raise ValidationError(
                f"الحساب {code} موجود بالفعل بنوع مختلف."
            )

        accounts[code] = account

    return accounts
