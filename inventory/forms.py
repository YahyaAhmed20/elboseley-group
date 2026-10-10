from decimal import Decimal

from django import forms
from django.db.models import Sum, Q, Value, F, DecimalField
from django.db.models.functions import Coalesce

from catalog.models import Item
from .models import StockMovement


class MovementForm(forms.Form):
    kind = forms.ChoiceField(
        choices=StockMovement.Kind.choices,
        label='نوع الحركة',
    )

    item = forms.ModelChoiceField(
        queryset=Item.objects.none(),
        label='الصنف',
        empty_label='— اختر الصنف —',
    )

    qty = forms.DecimalField(
        min_value=Decimal('0.01'),
        label='الكمية',
        widget=forms.NumberInput(attrs={'step': '0.01'}),
    )

    ref = forms.CharField(
        required=False,
        label='رقم المرجع',
        widget=forms.TextInput(
            attrs={'placeholder': 'فاتورة / أمر شغل'}
        ),
    )

    notes = forms.CharField(
        required=False,
        label='ملاحظة',
        widget=forms.Textarea(attrs={'rows': 2}),
    )

    def __init__(self, *args, kind='in', **kwargs):
        super().__init__(*args, **kwargs)

        self.kind = kind

        # لو إنشاء جديد
        if not self.is_bound:
            self.initial['kind'] = kind

        qs = (
            Item.objects
            .filter(is_active=True)
            .select_related('brand', 'unit')
            .annotate(
                total_in=Coalesce(
                    Sum(
                        'movements__qty',
                        filter=Q(movements__kind='in'),
                    ),
                    Value(0),
                    output_field=DecimalField(
                        max_digits=12,
                        decimal_places=2,
                    ),
                ),
                total_out=Coalesce(
                    Sum(
                        'movements__qty',
                        filter=Q(movements__kind='out'),
                    ),
                    Value(0),
                    output_field=DecimalField(
                        max_digits=12,
                        decimal_places=2,
                    ),
                ),
            )
            .annotate(
                balance=F('total_in') - F('total_out')
            )
        )

        # في حالة الصرف نعرض فقط الأصناف التي لها رصيد.
        if kind == StockMovement.Kind.OUT:
            qs = qs.filter(balance__gt=0)

        self.fields['item'].queryset = qs