
from django import forms

from catalog.models import Item
from supplier.models import Supplier
from .models import PurchaseInvoice


class PurchaseInvoiceForm(forms.Form):
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.none(),
        label="المورد",
    )
    invoice_number = forms.CharField(
        max_length=100,
        label="رقم الفاتورة",
    )
    payment_type = forms.ChoiceField(
        choices=PurchaseInvoice.PaymentType.choices,
        initial=PurchaseInvoice.PaymentType.CASH,
        label="نوع الدفع",
    )
    paid_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        initial=0,
        label="المبلغ المدفوع",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="ملاحظات",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["supplier"].queryset = Supplier.objects.filter(
            is_active=True
        )
        self.fields["supplier"].label_from_instance = (
            lambda supplier: f"{supplier.name} — {supplier.phone}"
            if supplier.phone
            else supplier.name
        )


class PurchaseInvoiceLineForm(forms.Form):
    item = forms.ModelChoiceField(
        queryset=Item.objects.none(),
        label="الصنف",
    )
    qty = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0.01,
        label="الكمية",
    )
    unit_price = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        label="سعر الوحدة",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["item"].queryset = Item.objects.filter(is_active=True)
