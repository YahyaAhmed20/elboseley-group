from django import forms
from .models import Supplier
class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'phone', 'opening_balance']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'اسم المورد'}),
            'phone': forms.TextInput(attrs={'placeholder': 'رقم الهاتف'}),
            'opening_balance': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
