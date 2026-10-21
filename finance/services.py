
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db.models import Sum, Case, When, F, DecimalField, Value
from django.db.models.functions import Coalesce

from .models import CashboxTransaction


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
