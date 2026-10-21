from decimal import Decimal

from django import forms
from django.db.models import Sum, Q, Value, F, DecimalField
from django.db.models.functions import Coalesce

from catalog.models import Item
from .models import StockMovement, StockIssue


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


class StockIssueForm(forms.ModelForm):
    class Meta:
        model = StockIssue
        fields = ["invoice_number", "recipient", "issue_type", "notes"]
        widgets = {
            "invoice_number": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "recipient": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "issue_type": forms.Select(
                attrs={"class": "form-select"}
            ),
            "notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
        }

    def clean_invoice_number(self):
        value = self.cleaned_data["invoice_number"].strip()
        if value.endswith("."):
            value = value[:-1].rstrip()
        if not value:
            raise forms.ValidationError("رقم فاتورة الصرف مطلوب.")
        return value


class StockIssueLineForm(forms.Form):
    item = forms.ModelChoiceField(
        queryset=Item.objects.none(),
        label="الصنف",
        empty_label="— اختر الصنف —",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    qty = forms.DecimalField(
        min_value=Decimal("0.01"),
        label="الكمية",
        widget=forms.NumberInput(
            attrs={"class": "form-control", "step": "0.01"}
        ),
    )
    unit_price = forms.DecimalField(
        min_value=Decimal("0"),
        initial=Decimal("0"),
        label="سعر الوحدة",
        widget=forms.NumberInput(
            attrs={"class": "form-control", "step": "0.01"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["item"].queryset = (
            Item.objects.filter(is_active=True)
            .select_related("unit")
            .order_by("name")
        )


StockIssueLineFormSet = forms.formset_factory(
    StockIssueLineForm,
    extra=1,
    min_num=1,
    max_num=10,
    validate_min=True,
    validate_max=True,
    can_delete=True,
)

StockIssueEditLineFormSet = forms.formset_factory(
    StockIssueLineForm,
    extra=0,
    min_num=1,
    max_num=10,
    validate_min=True,
    validate_max=True,
    can_delete=True,
)